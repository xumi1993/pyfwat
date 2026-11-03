"""GUI to align teleseismic waveforms, pick arrivals and delete bad traces.

Command-line tool: ``fwat_pick_tele``.
"""

import sys
import os
import argparse
try:
    from PySide6.QtCore import QCoreApplication, Qt
    from PySide6.QtGui import QIcon, QKeySequence, QShortcut, QWheelEvent
    from PySide6.QtWidgets import (
        QApplication, QFileDialog, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
        QMainWindow, QPushButton, QRadioButton, QSizePolicy, QVBoxLayout, QWidget,
    )
except ImportError as exc:
    raise ImportError(
        'GUI tools require PySide6. Install with: pip install "PySide6>=6.2"'
    ) from exc
from os.path import exists, dirname, join
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
from matplotlib.widgets import Cursor
from .picker_fig_tele import PickFig


class MyMplCanvas(FigureCanvas):
    """Qt canvas showing the picker figure."""
    def __init__(self, parent=None, path='', marker='a', enf=1,
                 xlim=[-50, 120], num=30, resample_dt=None):
        """Read the traces, create the figure and compute the MCCC arrivals.

        :param parent: Parent widget, defaults to None
        :type parent: PySide6.QtWidgets.QWidget, optional
        :param path: Event directory with the R- and Z-component SAC files
        :type path: str
        :param marker: SAC header of the reference arrival, defaults to ``'a'``
        :type marker: str, optional
        :param enf: Amplitude scale, defaults to 1
        :type enf: float, optional
        :param xlim: Time range in s around the arrival, defaults to ``[-50, 120]``
        :type xlim: list of float, optional
        :param num: Traces per page, defaults to 30
        :type num: int, optional
        :param resample_dt: Resampling interval in s, None to keep the original
            sampling, defaults to None
        :type resample_dt: float, optional
        """
        plt.rcParams['axes.unicode_minus'] = False 

        self.pf = PickFig(path, marker=marker, resample_dt=resample_dt)
        self.pf.para.xlim = xlim
        self.pf.para.enf = enf
        self.pf.para.num_per_page = num
        self.pf.init_figure()
        # self.pf.read_sac()
        self.pf.tdelta_mccc()

        FigureCanvas.__init__(self, self.pf.fig)
        self.setParent(parent)

        FigureCanvas.setSizePolicy(self,
                                   QSizePolicy.Policy.Expanding,
                                   QSizePolicy.Policy.Expanding)
        FigureCanvas.updateGeometry(self)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)


class MatplotlibWidget(QMainWindow):
    """Main window of the picker: control panel on the left, waveforms on the right.

    Click a trace to toggle whether it is kept; ``c``/``z`` or the mouse wheel
    change the page; *Save* deletes the bad traces and rewrites the others.
    """
    def __init__(self, path, marker='a', xlim=[-50, 120], enf=1,
                 pre_flt=None, num=30, align=False, resample_dt=None, parent=None):
        """:param path: Event directory with the R- and Z-component SAC files
        :type path: str
        :param marker: SAC header of the reference arrival, defaults to ``'a'``
        :type marker: str, optional
        :param xlim: Time range in s around the arrival, defaults to ``[-50, 120]``
        :type xlim: list of float, optional
        :param enf: Amplitude scale, defaults to 1
        :type enf: float, optional
        :param pre_flt: Band-pass corners ``[freqmin, freqmax]`` in Hz applied when
            the window opens, defaults to None
        :type pre_flt: list of float, optional
        :param num: Traces per page, defaults to 30
        :type num: int, optional
        :param align: Start aligned on the MCCC arrivals instead of the marker,
            defaults to False
        :type align: bool, optional
        :param resample_dt: Resampling interval in s, None to keep the original
            sampling, defaults to None
        :type resample_dt: float, optional
        :param parent: Parent widget, defaults to None
        :type parent: PySide6.QtWidgets.QWidget, optional
        """
        super(MatplotlibWidget, self).__init__(parent)
        self.xlim = xlim
        self.pre_flt = pre_flt
        self.enf = enf
        self.num = num
        self.resample_dt = resample_dt
        self.marker = marker
        self.align = align
        self.cursors = []
        self.initUi(path, marker)

    def initUi(self, path, marker):
        """Build the window, draw the traces and connect the mouse and keyboard.

        :param path: Event directory
        :type path: str
        :param marker: SAC header of the reference arrival
        :type marker: str
        """
        self.layout = QHBoxLayout()
        self._set_geom_center()
        self.mpl = MyMplCanvas(self, path=path, marker=marker, enf=self.enf,
                               xlim=self.xlim, num=self.num, resample_dt=self.resample_dt)

        self.main_frame = QWidget()
        self.setCentralWidget(self.main_frame)
        self.add_layout()
        self.plot_ui()
        self.mpl.mpl_connect('button_press_event', self.on_click)
        self.main_frame.setLayout(self.layout)
        self._define_global_shortcuts()
        self.setWindowTitle('Pick Teleseismic waveforms')

        # saveAction = QAction('&Save', self)        
        # saveAction.setShortcut('Ctrl+S')
        # saveAction.setStatusTip('Save this figure')
        # saveAction.triggered.connect(self.plot_save)

        # menubar = self.menuBar()
        # fileMenu = menubar.addMenu('&File')
        # fileMenu.addAction(saveAction)

        # self._define_global_shortcuts()
        
        self.setWindowIcon(QIcon(join(dirname(dirname(__file__)), 'data', 'icon.svg')))
    
    def add_layout(self):
        """Assemble the control panel and the canvas."""
        self.add_filter_box()
        self.add_align_box()
        self.add_plotting_box()
        self.add_saving_box()
        self.add_control_layout()
        # self.layout.addStretch(1)
        ctrlbox = QVBoxLayout()
        ctrlbox.addLayout(self.control_layout)
        ctrlbox.addWidget(self.plotting_box)
        ctrlbox.addWidget(self.filter_box)
        ctrlbox.addWidget(self.align_box)
        ctrlbox.addWidget(self.saving_box)
        ctrlbox.addStretch()
        self.layout.addLayout(ctrlbox)
        self.layout.addWidget(self.mpl, 2)

    def add_plotting_box(self):
        """Create the controls of the time range and amplitude scale."""
        self.plotting_box = QGroupBox('Plotting')
        self.plotting_box.setStyleSheet("QGroupBox {font-size: 18px; font-weight: bold;}")
        plotting_layout = QVBoxLayout()
        xlim_layout = QHBoxLayout()
        xlim_layout.addStretch(1)
        label_x = QLabel()
        label_x.setText('Time range (s):')
        self.xminEdit = QLineEdit()
        self.xminEdit.setText('{:.1f}'.format(self.mpl.pf.para.xlim[0]))
        self.xminEdit.textChanged.connect(self.on_xmin_changed)
        label_bar = QLabel()
        label_bar.setText('-')
        self.xmaxEdit = QLineEdit()
        self.xmaxEdit.setText('{:.1f}'.format(self.mpl.pf.para.xlim[1]))
        self.xmaxEdit.textChanged.connect(self.on_xmax_changed)
        xlim_layout.addWidget(label_x)
        xlim_layout.addWidget(self.xminEdit)
        xlim_layout.addWidget(label_bar)
        xlim_layout.addWidget(self.xmaxEdit)
        ampzoom_layout = QHBoxLayout()
        label_zoom = QLabel()
        label_zoom.setText('Amp zoom: ')
        self.ampzoomEdit = QLineEdit()
        self.ampzoomEdit.setText('{:.2f}'.format(self.mpl.pf.para.enf))
        self.ampzoomEdit.textChanged.connect(self.on_enf_changed)
        ampzoom_layout.addWidget(label_zoom)
        ampzoom_layout.addWidget(self.ampzoomEdit)
        self.ampzoomButton = QPushButton()
        self.ampzoomButton.setText('Confirm')
        self.ampzoomButton.clicked.connect(self.on_plot)
        plotting_layout.addLayout(xlim_layout)
        plotting_layout.addLayout(ampzoom_layout)
        plotting_layout.addWidget(self.ampzoomButton)
        self.plotting_box.setLayout(plotting_layout)

    def add_saving_box(self):
        """Create the controls of the cut window and the *Save* button."""
        self.saving_box = QGroupBox("Saving")
        self.saving_box.setStyleSheet("QGroupBox {font-size: 18px; font-weight: bold;}")
        save_layout = QVBoxLayout()
        cut_layout = QHBoxLayout()
        cut_layout.addStretch()
        label_x = QLabel()
        label_x.setText('Cut from')
        self.cutminEdit = QLineEdit()
        self.cutminEdit.setText('')
        self.cutminEdit.textChanged.connect(self.on_cutmin_changed)
        label_bar = QLabel()
        label_bar.setText('to')
        self.cutmaxEdit = QLineEdit()
        self.cutmaxEdit.setText('')
        self.cutmaxEdit.textChanged.connect(self.on_cutmax_changed)
        cut_layout.addWidget(label_x)
        cut_layout.addWidget(self.cutminEdit)
        cut_layout.addWidget(label_bar)
        cut_layout.addWidget(self.cutmaxEdit)
        save_layout.addLayout(cut_layout)
        self.saveButton = QPushButton()
        self.saveButton.setText('Save')
        self.saveButton.clicked.connect(self.on_save)
        save_layout.addWidget(self.saveButton)
        self.saving_box.setLayout(save_layout)

    def add_align_box(self):
        """Create the MCCC, arrival-picking and alignment controls."""
        self.align_box = QGroupBox("Alignment")
        self.align_box.setStyleSheet("QGroupBox {font-size: 18px; font-weight: bold;}")
        align_layout = QVBoxLayout()
        self.mcccButton = QPushButton()
        self.mcccButton.setText('Do MCCC')
        self.mcccButton.clicked.connect(self.on_do_mccc)
        self.pickButton = QPushButton()
        self.pickButton.setText('Pick arrival time')
        self.pickButton.setCheckable(True)
        self.pickButton.clicked.connect(self.on_pick_arr)
        align_layout.addWidget(self.mcccButton)
        align_layout.addWidget(self.pickButton)
        self.t0Radio = QRadioButton(f"Align with {self.marker}")
        self.t0Radio.setObjectName(self.marker)
        self.mcccRadio = QRadioButton("Align with MCCC")
        self.mcccRadio.setObjectName('mccc')
        if self.align:
            self.mcccRadio.setChecked(True)
            self.mpl.pf.para.align = 'mccc'
        else:
            self.t0Radio.setChecked(True)
            self.mpl.pf.para.align = self.marker
        self.t0Radio.toggled.connect(self.on_align)
        self.mcccRadio.toggled.connect(self.on_align)
        align_layout.addWidget(self.t0Radio)
        align_layout.addWidget(self.mcccRadio)
        self.align_box.setLayout(align_layout)

    def add_filter_box(self):
        """Create the band-pass filter controls and the *Restore* button."""
        self.filter_box = QGroupBox("Filter")
        self.filter_box.setStyleSheet("QGroupBox {font-size: 18px; font-weight: bold;}")
        self.Filter = QVBoxLayout()
        self.Filter.setContentsMargins(0, 0, 0, 0)
        self.Filter.setObjectName("Filter")
        self.label_3 = QLabel()
        self.label_3.setObjectName("label_3")
        self.Filter.addWidget(self.label_3)
        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.label = QLabel()
        self.label.setObjectName("label")
        self.horizontalLayout_2.addWidget(self.label)
        self.lineEdit_freqmin = QLineEdit()
        # self.lineEdit_freqmin.setObjectName("freqmin")
        self.lineEdit_freqmin.setText('{}'.format(self.pre_flt[0] if self.pre_flt is not None else ""))
        self.lineEdit_freqmin.textChanged.connect(self.on_freqmin_changed)
        self.horizontalLayout_2.addWidget(self.lineEdit_freqmin)
        self.Filter.addLayout(self.horizontalLayout_2)
        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.label_2 = QLabel()
        self.label_2.setObjectName("label_2")
        self.horizontalLayout_3.addWidget(self.label_2)
        self.lineEdit_freqmax = QLineEdit()
        self.lineEdit_freqmax.setText('{}'.format(self.pre_flt[1] if self.pre_flt is not None else ""))
        # self.lineEdit_freqmax.setObjectName("freqmax")
        self.lineEdit_freqmax.textChanged.connect(self.on_freqmax_changed)
        self.horizontalLayout_3.addWidget(self.lineEdit_freqmax)
        self.Filter.addLayout(self.horizontalLayout_3)
        self.fltButton = QPushButton()
        # self.fltButton.setObjectName("pushButton")
        self.Filter.addWidget(self.fltButton)
        self.fltButton.clicked.connect(self.on_filter)
        self.restoreButton = QPushButton('Restore')
        self.Filter.addWidget(self.restoreButton)
        self.restoreButton.clicked.connect(self.on_restore)
        _translate = QCoreApplication.translate
        self.label.setText(_translate("Dialog", "Min Frequency (Hz):"))
        self.label_2.setText(_translate("Dialog", "Max Frequency (Hz):"))
        self.fltButton.setText(_translate("Dialog", "Confirm"))
        self.filter_box.setLayout(self.Filter)

    def add_control_layout(self):
        """Create the page buttons."""
        self.control_layout = QHBoxLayout()
        self.pagedown = QPushButton('Page Down (z)')
        self.pageup = QPushButton('Page Up (c)')
        self.pagedown.clicked.connect(self.previous_connect)
        self.pageup.clicked.connect(self.next_connect)
        self.control_layout.addWidget(self.pagedown)
        self.control_layout.addWidget(self.pageup)

    def _define_global_shortcuts(self):
        """Bind ``c`` to the next page and ``z`` to the previous page."""
        self.key_c = QShortcut(QKeySequence('c'), self)
        self.key_c.activated.connect(self.next_connect)
        self.key_c.setContext(Qt.ShortcutContext.ApplicationShortcut)
        self.key_z = QShortcut(QKeySequence('z'), self)
        self.key_z.activated.connect(self.previous_connect)
        self.key_z.setContext(Qt.ShortcutContext.ApplicationShortcut)
        # self.key_space = QShortcut(QKeySequence('Space'), self)
        # self.key_space.activated.connect(self.plot_ui)
    
    def wheelEvent(self, event: QWheelEvent):
        """Scroll up for the next page and down for the previous page.

        :param event: Wheel event
        :type event: PySide6.QtGui.QWheelEvent
        """
        if event.angleDelta().y() > 0:
            self.mpl.pf.page_up()
        else:
            self.mpl.pf.page_down()
        self.mpl.pf.setup_figure()
        self.mpl.draw_idle()

    def previous_connect(self):
        """Show the previous page."""
        self.mpl.pf.page_down()
        self.mpl.pf.setup_figure()
        self.mpl.draw_idle()
    
    def next_connect(self):
        """Show the next page."""
        self.mpl.pf.page_up()
        self.mpl.pf.setup_figure()
        self.mpl.draw_idle()

    def on_click(self, event):
        """Shift the arrivals to the clicked time in picking mode, otherwise toggle the clicked trace.

        :param event: Mouse click event
        :type event: matplotlib.backend_bases.MouseEvent
        """
        if self.pickButton.isChecked():
            self.mpl.pf.onclick_arr(event)
            self.replot_fig()
        else:
            self.mpl.pf.onclick(event)
        self.mpl.draw_idle()

    def on_cutmin_changed(self):
        """Set the start of the cut window from its text box; invalid text clears it."""
        text = self.cutminEdit.text()
        try:
            self.mpl.pf.para.cut_win[0] = float(text)
        except:
            self.mpl.pf.para.cut_win[0] = None
            self.cutminEdit.setText('')
    
    def on_pick_arr(self, event):
        """Turn the arrival-picking mode with a vertical cursor on or off.

        :param event: Value sent by the button's ``clicked`` signal
        """
        if self.pickButton.isChecked():
            QApplication.setOverrideCursor(Qt.CursorShape.CrossCursor)
            for ax in self.mpl.pf.axes:
                self.cursors.append(Cursor(ax, horizOn=False, vertOn=True, useblit=True, color='k', alpha=0.5))
        else:
            QApplication.restoreOverrideCursor()
            for cursor in self.cursors:
                cursor.clear(event)
            self.cursors.clear()
            self.mpl.draw_idle()

    def on_cutmax_changed(self):
        """Set the end of the cut window from its text box; invalid text clears it."""
        text = self.cutmaxEdit.text()
        try:
            self.mpl.pf.para.cut_win[1] = float(text)
        except:
            self.mpl.pf.para.cut_win[1] = None
            self.cutmaxEdit.setText('')

    def on_xmin_changed(self):
        """Set the start of the time range from its text box; invalid text restores the previous value."""
        try:
            self.mpl.pf.para.xlim[0] = float(self.xminEdit.text())
        except:
            self.xminEdit.setText('{:.1f}'.format(self.mpl.pf.para.xlim[0]))
    
    def on_xmax_changed(self):
        """Set the end of the time range from its text box; invalid text restores the previous value."""
        try:
            self.mpl.pf.para.xlim[1] = float(self.xmaxEdit.text())
        except:
            self.xmaxEdit.setText('{:.1f}'.format(self.mpl.pf.para.xlim[1]))

    def on_enf_changed(self):
        """Set the amplitude scale from its text box; invalid text restores the previous value."""
        try:
            self.mpl.pf.para.enf = float(self.ampzoomEdit.text())
        except:
            self.ampzoomEdit.setText('{:.1f}'.format(self.mpl.pf.para.enf))
    
    def on_freqmin_changed(self):
        """Set the lower corner frequency from its text box; invalid text is ignored."""
        try:
            self.mpl.pf.para.freqmin = float(self.lineEdit_freqmin.text())
        except:
            pass

    def on_freqmax_changed(self):
        """Set the upper corner frequency from its text box; invalid text is ignored."""
        try:
            self.mpl.pf.para.freqmax = float(self.lineEdit_freqmax.text())
        except:
            pass
    
    def on_save(self):
        """Save the selection to the data directory and redraw."""
        self.mpl.pf.save()
        self.mpl.pf.reset()
        self.mpl.pf.plot_seis()
        self.mpl.pf.setup_figure()
        self.mpl.draw_idle()

    def on_plot(self):
        """Redraw with the new time range and amplitude scale, unless the range is reversed."""
        if self.mpl.pf.para.xlim[1] < self.mpl.pf.para.xlim[0]:
            return
        self.replot_fig()
        self.mpl.draw_idle()
    
    def replot_fig(self):
        """Clear the axes and redraw the traces, keeping bad traces gray."""
        for ax in self.mpl.pf.axes:
            ax.cla()
        self.mpl.pf.plot_seis()
        self.mpl.pf._set_gray()
        self.mpl.pf.setup_figure()

    def on_filter(self):
        """Filter the raw traces with the current band and redraw."""
        self.mpl.pf.filter(renew=True)
        self.replot_fig()
        self.mpl.draw_idle()
    
    def on_restore(self):
        """Discard filtering and redraw."""
        self.mpl.pf.restore()
        self.replot_fig()
        self.mpl.draw_idle()

    def on_align(self):
        """Align on the marker or the MCCC arrivals, following the checked radio button."""
        btn = self.sender()
        if btn.isChecked():
            self.mpl.pf.para.align = btn.objectName()
            self.replot_fig()
            self.mpl.draw_idle()
    
    def on_do_mccc(self):
        """Recompute the MCCC arrivals and redraw."""
        self.mpl.pf.tdelta_mccc()
        self.replot_fig()
        self.mpl.draw_idle()

    # def enlarge(self):
    #     self.mpl.rffig.enlarge()
    #     self.mpl.draw()

    # def reduce(self):
    #     self.mpl.rffig.reduce()
    #     self.mpl.draw()

    # def finish(self):
    #     self.mpl.rffig.finish()
    #     QApplication.quit()

    def plot_ui(self):
        """Apply the initial filter and draw the traces."""
        if self.pre_flt is not None:
            self.mpl.pf.para.freqmin = self.pre_flt[0]
            self.mpl.pf.para.freqmax = self.pre_flt[1]
        self.mpl.pf.filter()
        self.mpl.pf.plot_seis()
        self.mpl.pf.setup_figure()

    def plot_save(self):
        """Not used: left over from an older receiver-function GUI and refers to
        attributes this window does not have.
        """
        if self.only_r:
            default_name = 'R_bazorder'
        else:
            default_name = 'RT_bazorder'
        fileName_choose, filetype = QFileDialog.getSaveFileName(self,
                                    "Save the figure",
                                    os.path.join(os.getcwd(), self.mpl.rffig.staname + default_name), 
                                    "PDF Files (*.pdf);;Images (*.png);;All Files (*)")

        if fileName_choose == "":
            return
        if not hasattr(self.mpl.rffig, 'plotfig'):
            self.mpl.rffig.plot()
        try:
            self.mpl.rffig.plotfig.savefig(fileName_choose, dpi=500, bbox_inches='tight')
            self.mpl.rffig.log.RFlog.info('Figure saved to {}'.format(fileName_choose))
        except Exception as e:
            self.mpl.rffig.log.RFlog.error('{}'.format(e))

    def _set_geom_center(self, height=1, width=1):
        """Resize the window to a fraction of the screen and center it.

        :param height: Fraction of the screen height, defaults to 1
        :type height: float, optional
        :param width: Fraction of the screen width, defaults to 1
        :type width: float, optional
        """
        screen_resolution = self.screen().availableGeometry()
        screen_height = screen_resolution.height()
        screen_width = screen_resolution.width()
        self.frame_height = int(screen_height * height)
        self.frame_width = int(screen_width * width)

        self.resize(self.frame_width, self.frame_height)
        frame_geometry = self.frameGeometry()
        frame_geometry.moveCenter(screen_resolution.center())
        self.move(frame_geometry.topLeft())

    def add_btn(self):
        """Not used: left over from an older receiver-function GUI and refers to
        methods this window does not have.
        """
        pre_btn = QPushButton("Back (z)")
        pre_btn.clicked.connect(self.previous_connect)
        next_btn = QPushButton("Next (c)")
        next_btn.clicked.connect(self.next_connect)
        plot_btn = QPushButton("Preview (Space)")
        plot_btn.clicked.connect(self.plot_ui)
        finish_btn = QPushButton("Finish")
        finish_btn.clicked.connect(self.finish)
        btnbox = QHBoxLayout()
        btnbox.addStretch(1)
        btnbox.addWidget(pre_btn)
        btnbox.addWidget(next_btn)
        btnbox.addWidget(plot_btn)
        btnbox.addWidget(finish_btn)

        enlarge_btn = QPushButton("Amp enlarge")
        enlarge_btn.clicked.connect(self.enlarge)
        areduce_btn = QPushButton("Amp reduce")
        areduce_btn.clicked.connect(self.reduce)
        pathbox = QHBoxLayout()
        pathbox.addWidget(enlarge_btn)
        pathbox.addWidget(areduce_btn)

        ctrl_layout = QHBoxLayout()
        ctrl_layout.addLayout(pathbox)
        ctrl_layout.addLayout(btnbox)

        self.layout.addLayout(ctrl_layout)


def main():
    """Command-line entry point of ``fwat_pick_tele``."""
    parser = argparse.ArgumentParser(description="User interface for picking teleseismic waveforms")
    parser.add_argument('path', type=str, help='Path to data directory')
    parser.add_argument('-c', help='Align with corrected arrival time', action='store_true')
    parser.add_argument('-d', help='Resample dt, defaults to 0.01. set to NA to use raw rampling rate.', default=0.01, metavar='dt')
    parser.add_argument('-e', help='enlarge coefficient, defaults to 1', type=float, default=1, metavar='coef')
    parser.add_argument('-f', help="pre-filter on waveforms", default=None, metavar='0.05/1.0')
    parser.add_argument('-m', help='marker for picking', default='a', metavar='marker')
    parser.add_argument('-n', help='number of traces per page', default=30, type=int, metavar='num')
    parser.add_argument('-x', help="Set x limits of the current axes, defaults to [-50, 120]",
                        dest='xlim', default='-50/120', metavar='xmin/xmax')
    arg = parser.parse_args()
    path = arg.path
    if arg.f is None:
        pre_flt = arg.f
    else:
        pre_flt = [float(v) for v in arg.f.split('/')]
    if arg.d == 'NA':
        resample_dt = None
    else:
        try:
            resample_dt = float(arg.d)
        except:
            raise ValueError('Resample dt must be a number or NA')
    try:
        xlim = [float(v) for v in arg.xlim.split('/')]
    except:
        raise ValueError('Xlim must be a string like xmin/xmax in seconds')
    if not exists(path):
        raise FileNotFoundError('No such directory of {}'.format(path))
    app = QApplication(sys.argv)
    ui = MatplotlibWidget(path, marker=arg.m, pre_flt=pre_flt, enf=arg.e, num=arg.n,
                          align=arg.c, resample_dt=resample_dt, xlim=xlim)
    ui.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
