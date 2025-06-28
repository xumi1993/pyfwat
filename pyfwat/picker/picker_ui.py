import sys
import os
import argparse
# matplotlib.use("Qt5Agg")
try:
    from PyQt5.QtCore import Qt
    from PyQt5.QtGui import QIcon, QKeySequence, QWheelEvent
    from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, \
                                QSizePolicy, QWidget, QDesktopWidget, \
                                QPushButton, QHBoxLayout, QFileDialog, \
                                QAction, QShortcut, QLabel, QLineEdit, \
                                QGroupBox, QRadioButton
    from PyQt5.QtCore import QRect, QCoreApplication, pyqtSlot, QMetaObject 
except:
    raise("Please install PyQt5 first: pip install PyQt5")
from os.path import exists, dirname, join
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
from matplotlib.widgets import Cursor
from .picker_fig import PickFig
import glob


class MyMplCanvas(FigureCanvas):
    def __init__(self, parent=None, path='', marker='a', enf=1,
                 xlim=[-50, 120], num=30, resample_dt=None):

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
                                   QSizePolicy.Expanding,
                                   QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)


class MatplotlibWidget(QMainWindow):
    def __init__(self, path, marker='a', xlim=[-50, 120], enf=1,
                 pre_flt=None, num=30, align=False, resample_dt=None, parent=None):
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
        QMetaObject.connectSlotsByName(self)

    def initUi(self, path, marker):
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
        self.plotting_box = QGroupBox('Plotting')
        self.plotting_box.setStyleSheet("QGroupBox {font-size: 18px; font-weight: bold;}")
        plotting_layout = QVBoxLayout()
        xlim_layout = QHBoxLayout()
        xlim_layout.addStretch(1)
        label_x = QLabel()
        label_x.setText('Limitation of X-axis (s):')
        self.xminEdit = QLineEdit()
        self.xminEdit.setFixedWidth(40)
        self.xminEdit.setText('{:.1f}'.format(self.mpl.pf.para.xlim[0]))
        self.xminEdit.textChanged.connect(self.on_xmin_changed)
        self.xminEdit.setFocusPolicy(Qt.NoFocus)
        label_bar = QLabel()
        label_bar.setText('-')
        self.xmaxEdit = QLineEdit()
        self.xmaxEdit.setFixedWidth(40)
        self.xmaxEdit.setText('{:.1f}'.format(self.mpl.pf.para.xlim[1]))
        self.xmaxEdit.textChanged.connect(self.on_xmax_changed)
        self.xmaxEdit.setFocusPolicy(Qt.NoFocus)
        xlim_layout.addWidget(label_x)
        xlim_layout.addWidget(self.xminEdit)
        xlim_layout.addWidget(label_bar)
        xlim_layout.addWidget(self.xmaxEdit)
        ampzoom_layout = QHBoxLayout()
        label_zoom = QLabel()
        label_zoom.setText('Amp zoom: ')
        self.ampzoomEdit = QLineEdit()
        self.ampzoomEdit.setText('{:.1e}'.format(self.mpl.pf.para.enf))
        self.ampzoomEdit.textChanged.connect(self.on_enf_changed)
        self.ampzoomEdit.setFocusPolicy(Qt.NoFocus)
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
        self.saving_box = QGroupBox("Saving")
        self.saving_box.setStyleSheet("QGroupBox {font-size: 18px; font-weight: bold;}")
        save_layout = QVBoxLayout()
        cut_layout = QHBoxLayout()
        cut_layout.addStretch()
        label_x = QLabel()
        label_x.setText('Cut from')
        self.cutminEdit = QLineEdit()
        self.cutminEdit.setFixedWidth(40)
        self.cutminEdit.setText('')
        self.cutminEdit.textChanged.connect(self.on_cutmin_changed)
        self.cutminEdit.setFocusPolicy(Qt.NoFocus)
        label_bar = QLabel()
        label_bar.setText('to')
        self.cutmaxEdit = QLineEdit()
        self.cutmaxEdit.setFixedWidth(40)
        self.cutmaxEdit.setText('')
        self.cutmaxEdit.textChanged.connect(self.on_cutmax_changed)
        self.cutmaxEdit.setFocusPolicy(Qt.NoFocus)
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
        self.lineEdit_freqmin.setText('{}'.format(self.pre_flt[0] if self.pre_flt is not None else None))
        self.lineEdit_freqmin.textChanged.connect(self.on_freqmin_changed)
        self.horizontalLayout_2.addWidget(self.lineEdit_freqmin)
        self.Filter.addLayout(self.horizontalLayout_2)
        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.label_2 = QLabel()
        self.label_2.setObjectName("label_2")
        self.horizontalLayout_3.addWidget(self.label_2)
        self.lineEdit_freqmax = QLineEdit()
        self.lineEdit_freqmax.setText('{}'.format(self.pre_flt[1] if self.pre_flt is not None else None))
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
        self.control_layout = QHBoxLayout()
        self.pagedown = QPushButton('Page Down (z)')
        self.pageup = QPushButton('Page Up (c)')
        self.pagedown.clicked.connect(self.previous_connect)
        self.pageup.clicked.connect(self.next_connect)
        self.control_layout.addWidget(self.pagedown)
        self.control_layout.addWidget(self.pageup)

    def _define_global_shortcuts(self):
        self.key_c = QShortcut(QKeySequence('c'), self)
        self.key_c.activated.connect(self.next_connect)
        self.key_z = QShortcut(QKeySequence('z'), self)
        self.key_z.activated.connect(self.previous_connect)
        # self.key_space = QShortcut(QKeySequence('Space'), self)
        # self.key_space.activated.connect(self.plot_ui)
    
    def wheelEvent(self, event: QWheelEvent):
        if event.angleDelta().y() > 0:
            self.mpl.pf.page_up()
        else:
            self.mpl.pf.page_down()
        self.mpl.pf.setup_figure()
        self.mpl.draw_idle()

    def previous_connect(self):
        self.mpl.pf.page_down()
        self.mpl.pf.setup_figure()
        self.mpl.draw_idle()
    
    def next_connect(self):
        self.mpl.pf.page_up()
        self.mpl.pf.setup_figure()
        self.mpl.draw_idle()

    def on_click(self, event):
        if self.pickButton.isChecked():
            self.mpl.pf.onclick_arr(event)
            self.replot_fig()
        else:
            self.mpl.pf.onclick(event)
        self.mpl.draw_idle()

    def on_cutmin_changed(self):
        text = self.cutminEdit.text()
        try:
            self.mpl.pf.para.cut_win[0] = float(text)
        except:
            self.mpl.pf.para.cut_win[0] = None
            self.cutminEdit.setText('')
    
    def on_pick_arr(self, event):
        if self.pickButton.isChecked():
            QApplication.setOverrideCursor(Qt.CrossCursor)
            for ax in self.mpl.pf.axes:
                self.cursors.append(Cursor(ax, horizOn=False, vertOn=True, useblit=True, color='k', alpha=0.5))
        else:
            QApplication.restoreOverrideCursor()
            for cursor in self.cursors:
                cursor.clear(event)
            self.cursors.clear()
            self.mpl.draw_idle()

    def on_cutmax_changed(self):
        text = self.cutmaxEdit.text()
        try:
            self.mpl.pf.para.cut_win[1] = float(text)
        except:
            self.mpl.pf.para.cut_win[1] = None
            self.cutmaxEdit.setText('')

    def on_xmin_changed(self):
        try:
            self.mpl.pf.para.xlim[0] = float(self.xminEdit.text())
        except:
            self.xminEdit.setText('{:.1f}'.format(self.mpl.pf.para.xlim[0]))
    
    def on_xmax_changed(self):
        try:
            self.mpl.pf.para.xlim[1] = float(self.xmaxEdit.text())
        except:
            self.xmaxEdit.setText('{:.1f}'.format(self.mpl.pf.para.xlim[1]))

    def on_enf_changed(self):
        try:
            self.mpl.pf.para.enf = float(self.ampzoomEdit.text())
        except:
            self.ampzoomEdit.setText('{:.1f}'.format(self.mpl.pf.para.enf))
    
    def on_freqmin_changed(self):
        try:
            self.mpl.pf.para.freqmin = float(self.lineEdit_freqmin.text())
        except:
            pass

    def on_freqmax_changed(self):
        try:
            self.mpl.pf.para.freqmax = float(self.lineEdit_freqmax.text())
        except:
            pass
    
    def on_save(self):
        self.mpl.pf.save()
        self.mpl.pf.reset()
        self.mpl.pf.plot_seis()
        self.mpl.pf.setup_figure()
        self.mpl.draw_idle()

    def on_plot(self):
        if self.mpl.pf.para.xlim[1] < self.mpl.pf.para.xlim[0]:
            return
        self.replot_fig()
        self.mpl.draw_idle()
    
    def replot_fig(self):
        for ax in self.mpl.pf.axes:
            ax.cla()
        self.mpl.pf.plot_seis()
        self.mpl.pf._set_gray()
        self.mpl.pf.setup_figure()

    def on_filter(self):
        self.mpl.pf.filter(renew=True)
        self.replot_fig()
        self.mpl.draw_idle()
    
    def on_restore(self):
        self.mpl.pf.restore()
        self.replot_fig()
        self.mpl.draw_idle()

    def on_align(self):
        btn = self.sender()
        if btn.isChecked():
            self.mpl.pf.para.align = btn.objectName()
            self.replot_fig()
            self.mpl.draw_idle()
    
    def on_do_mccc(self):
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
        if self.pre_flt is not None:
            self.mpl.pf.para.freqmin = self.pre_flt[0]
            self.mpl.pf.para.freqmax = self.pre_flt[1]
        self.mpl.pf.filter()
        self.mpl.pf.plot_seis()
        self.mpl.pf.setup_figure()

    def plot_save(self):
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
        screen_resolution = QDesktopWidget().screenGeometry()
        screen_height = screen_resolution.height()
        screen_width = screen_resolution.width()
        self.frame_height = int(screen_height * height)
        self.frame_width = int(screen_width * width)

        self.setGeometry(0, 0, self.frame_width, self.frame_height)
        self.move(int((screen_width / 2) - (self.frameSize().width() / 2)),
                  int((screen_height / 2) - (self.frameSize().height() / 2)))

    def add_btn(self):
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
    parser = argparse.ArgumentParser(description="User interface for picking PRFs")
    parser.add_argument('path', type=str, help='Path to data directory')
    parser.add_argument('-c', help='Align with corrected arrival time', action='store_true')
    parser.add_argument('-d', help='Resample dt, defaults to 0.01. set to NA to use raw rampling rate.', default=0.01, metavar='dt')
    parser.add_argument('-e', help='enlarge coefficient, defaults to 1', type=float, default=1, metavar='coef')
    parser.add_argument('-f', help="pre-filter on waveforms", default=None, metavar='0.05/1.0')
    parser.add_argument('-m', help='marker for picking', default='a', metavar='marker')
    parser.add_argument('-n', help='number of traces per page', default=30, type=int, metavar='num')
    parser.add_argument('-x', help="Set x limits of the current axes, defaults to [-20, 120]",
                        dest='xlim', default=None, type=float, metavar='xmin/xmax')
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
    if not exists(path):
        raise FileNotFoundError('No such directory of {}'.format(path))
    app = QApplication(sys.argv)
    ui = MatplotlibWidget(path, marker=arg.m, pre_flt=pre_flt, enf=arg.e, num=arg.n, align=arg.c, resample_dt=resample_dt)
    ui.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
