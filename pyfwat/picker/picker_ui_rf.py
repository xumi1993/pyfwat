#!/usr/bin/env python3
"""Interactive PySide6 GUI for reviewing and deleting receiver functions."""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

# os.environ.setdefault("MPLCONFIGDIR", "/tmp/lms_spn_rf_picker_matplotlib")

try:
    from PySide6.QtCore import QEvent, QTimer, Qt
    from PySide6.QtGui import QColor
    from PySide6.QtWidgets import (
        QApplication,
        QDoubleSpinBox,
        QFileDialog,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QListWidget,
        QListWidgetItem,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QSlider,
        QSplitter,
        QVBoxLayout,
        QWidget,
    )
except ImportError as exc:
    raise ImportError(
        'GUI tools require PySide6. Install with: pip install "PySide6>=6.2"'
    ) from exc

import numpy as np
from matplotlib.backends.backend_qtagg import (
    FigureCanvasQTAgg as FigureCanvas,
)
from matplotlib.figure import Figure
from obspy import read


DEFAULT_PATTERN = "*.*.BXR.F*.rf.sac"
ROWS_PER_VIEW = 18
POSITIVE_COLOR = "#d73027"
NEGATIVE_COLOR = "#4575b4"
SELECTED_COLOR = "#909090"
FILL_ALPHA = 0.42
STATION_PATTERN = re.compile(
    r"^(?P<network>[^.]+)\.(?P<station>[^.]+)\."
    r"(?P<channel>BXR)\.F(?P<gauss>[0-9.]+)\.rf\.sac$",
    re.IGNORECASE,
)


@dataclass
class RFRecord:
    """A receiver function loaded from a SAC file.

    :ivar path: Path to the SAC file
    :ivar network: Network code
    :ivar station: Station code
    :ivar channel: Channel code
    :ivar gauss: Gaussian factor from the file name, None if unknown
    :ivar times: Sample times in s relative to the SAC ``b`` reference
    :ivar data: Amplitudes, with non-finite values set to 0
    """
    path: Path
    network: str
    station: str
    channel: str
    gauss: float | None
    times: np.ndarray
    data: np.ndarray


def natural_station_key(station: str) -> tuple[str, int, str]:
    """Sort key that orders station codes such as ``ST2`` before ``ST10``.

    :param station: Station code
    :type station: str
    :return: Upper-case letter prefix, numeric suffix (-1 if the code is not
        letters followed by digits) and the original code
    :rtype: tuple
    """
    match = re.fullmatch(r"([A-Za-z]+)(\d+)", station)
    if match is None:
        return station, -1, station
    prefix, number = match.groups()
    return prefix.upper(), int(number), station


def file_metadata(path: Path) -> tuple[str, str, str, float | None]:
    """Network, station, channel and Gaussian factor from a file name.

    Names like ``NET.STA.BXR.F2.5.rf.sac`` are parsed fully; otherwise the first
    three dot-separated fields are used and the Gaussian factor is None.

    :param path: Path to the SAC file
    :type path: pathlib.Path
    :return: Network, station, channel and Gaussian factor
    :rtype: tuple
    """
    match = STATION_PATTERN.match(path.name)
    if match is not None:
        gauss_text = match.group("gauss")
        try:
            gauss = float(gauss_text)
        except ValueError:
            gauss = None
        return (
            match.group("network"),
            match.group("station"),
            match.group("channel"),
            gauss,
        )
    fields = path.name.split(".")
    network = fields[0] if fields else ""
    station = fields[1] if len(fields) > 1 else path.stem
    channel = fields[2] if len(fields) > 2 else ""
    return network, station, channel, None


def load_rf_record(path: Path) -> RFRecord:
    """Read a single-trace SAC file into an :class:`RFRecord`.

    :param path: Path to the SAC file
    :type path: pathlib.Path
    :raises RuntimeError: If the file does not hold exactly one trace or has no
        finite samples
    :return: The loaded receiver function
    :rtype: RFRecord
    """
    stream = read(str(path))
    if len(stream) != 1:
        raise RuntimeError(f"expected one trace, found {len(stream)}")
    trace = stream[0]
    data = np.asarray(trace.data, dtype=float)
    if data.size < 2 or not np.isfinite(data).any():
        raise RuntimeError("trace has no finite waveform samples")
    data = np.nan_to_num(data, nan=0.0, posinf=0.0, neginf=0.0)
    begin = (
        float(trace.stats.sac.b)
        if hasattr(trace.stats, "sac") and hasattr(trace.stats.sac, "b")
        else 0.0
    )
    times = begin + np.arange(trace.stats.npts) * trace.stats.delta
    network, station, channel, gauss = file_metadata(path)
    return RFRecord(
        path=path,
        network=network,
        station=station,
        channel=channel,
        gauss=gauss,
        times=times,
        data=data,
    )


class RFPickerWindow(QMainWindow):
    """Window to review the receiver functions of an event and delete bad ones.

    Click a waveform or check a station to mark it; ``z``/``c`` change the page;
    the delete button permanently removes the marked SAC files.
    """
    def __init__(self, initial_directory: Path | None = None) -> None:
        """:param initial_directory: Event directory to load on start, defaults to None
        :type initial_directory: pathlib.Path, optional
        """
        super().__init__()
        self.setWindowTitle("Receiver Function Picker — PySide6")
        self.resize(1450, 900)

        self.records: list[RFRecord] = []
        self.selected: set[int] = set()
        self.view_start = 0
        self.visible_indices: list[int] = []
        self.artists: dict[int, tuple] = {}
        self._updating_list = False
        self.global_amplitude = 1.0

        self._build_interface()
        QApplication.instance().installEventFilter(self)
        if initial_directory is not None:
            self.directory_edit.setText(str(initial_directory))
            self.load_directory(initial_directory)

    def _build_interface(self) -> None:
        """Create the directory, display and selection controls and the canvas."""
        central = QWidget()
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(8, 8, 8, 8)
        root_layout.setSpacing(7)
        self.setCentralWidget(central)

        directory_row = QHBoxLayout()
        directory_row.addWidget(QLabel("Receiver Function Directory"))
        self.directory_edit = QLineEdit()
        self.directory_edit.setPlaceholderText(
            "Select an event directory containing WC.*.BXR.F*.rf.sac files"
        )
        self.directory_edit.returnPressed.connect(self.load_from_text)
        directory_row.addWidget(self.directory_edit, 1)
        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self.browse_directory)
        directory_row.addWidget(browse_button)
        load_button = QPushButton("Load")
        load_button.clicked.connect(self.load_from_text)
        directory_row.addWidget(load_button)
        root_layout.addLayout(directory_row)

        control_row = QHBoxLayout()
        control_row.addWidget(QLabel("File pattern"))
        self.pattern_edit = QLineEdit(DEFAULT_PATTERN)
        self.pattern_edit.setMaximumWidth(235)
        control_row.addWidget(self.pattern_edit)

        control_row.addSpacing(12)
        control_row.addWidget(QLabel("Time range"))
        self.xmin_spin = QDoubleSpinBox()
        self.xmin_spin.setRange(-10000.0, 10000.0)
        self.xmin_spin.setDecimals(1)
        self.xmin_spin.setValue(-1.0)
        self.xmin_spin.setSuffix(" s")
        self.xmin_spin.setMaximumWidth(95)
        control_row.addWidget(self.xmin_spin)
        control_row.addWidget(QLabel("to"))
        self.xmax_spin = QDoubleSpinBox()
        self.xmax_spin.setRange(-10000.0, 10000.0)
        self.xmax_spin.setDecimals(1)
        self.xmax_spin.setValue(15.0)
        self.xmax_spin.setSuffix(" s")
        self.xmax_spin.setMaximumWidth(95)
        control_row.addWidget(self.xmax_spin)
        range_button = QPushButton("Apply")
        range_button.clicked.connect(self.apply_time_range)
        control_row.addWidget(range_button)
        full_range_button = QPushButton("Full range")
        full_range_button.clicked.connect(self.show_full_time_range)
        control_row.addWidget(full_range_button)

        control_row.addSpacing(12)
        control_row.addWidget(QLabel("Amplitude (global normalization)"))
        self.scale_slider = QSlider(Qt.Orientation.Horizontal)
        self.scale_slider.setRange(10, 300)
        self.scale_slider.setValue(180)
        self.scale_slider.setMaximumWidth(150)
        self.scale_slider.valueChanged.connect(self.update_scale)
        control_row.addWidget(self.scale_slider)
        control_row.addStretch(1)
        root_layout.addLayout(control_row)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        root_layout.addWidget(splitter, 1)

        list_panel = QWidget()
        list_layout = QVBoxLayout(list_panel)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.addWidget(QLabel("Stations (check to mark for deletion)"))
        self.station_list = QListWidget()
        self.station_list.itemChanged.connect(self.on_list_item_changed)
        list_layout.addWidget(self.station_list, 1)

        paging_row = QHBoxLayout()
        self.previous_page_button = QPushButton("Previous page (Z)")
        self.previous_page_button.clicked.connect(lambda: self.change_page(-1))
        self.previous_page_button.setEnabled(False)
        paging_row.addWidget(self.previous_page_button)
        self.next_page_button = QPushButton("Next page (C)")
        self.next_page_button.clicked.connect(lambda: self.change_page(1))
        self.next_page_button.setEnabled(False)
        paging_row.addWidget(self.next_page_button)
        list_layout.addLayout(paging_row)
        splitter.addWidget(list_panel)

        plot_panel = QWidget()
        plot_layout = QVBoxLayout(plot_panel)
        plot_layout.setContentsMargins(0, 0, 0, 0)
        self.figure = Figure(figsize=(11, 8), constrained_layout=True)
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        plot_layout.addWidget(self.canvas, 1)
        splitter.addWidget(plot_panel)
        splitter.setSizes([280, 1120])

        action_row = QHBoxLayout()
        select_all_button = QPushButton("Select all")
        select_all_button.clicked.connect(self.select_all)
        action_row.addWidget(select_all_button)
        clear_button = QPushButton("Clear selection")
        clear_button.clicked.connect(self.clear_selection)
        action_row.addWidget(clear_button)
        invert_button = QPushButton("Invert selection")
        invert_button.clicked.connect(self.invert_selection)
        action_row.addWidget(invert_button)
        action_row.addSpacing(12)
        delete_button = QPushButton("Permanently delete selected original SAC files")
        delete_button.setStyleSheet(
            "QPushButton { color: #a51616; font-weight: bold; }"
        )
        delete_button.clicked.connect(self.delete_selected_files)
        action_row.addWidget(delete_button)
        action_row.addStretch(1)
        self.status_label = QLabel("No receiver functions loaded")
        action_row.addWidget(self.status_label)
        root_layout.addLayout(action_row)

        self.canvas.mpl_connect("button_press_event", self.on_canvas_click)

    def showEvent(self, event) -> None:
        """Focus the canvas once the window is shown, so that page keys work.

        :param event: Show event
        :type event: PySide6.QtGui.QShowEvent
        """
        super().showEvent(event)
        if self.records:
            QTimer.singleShot(0, self.focus_canvas)

    def focus_canvas(self) -> None:
        """Give keyboard focus to the canvas."""
        self.canvas.setFocus(Qt.FocusReason.OtherFocusReason)

    def browse_directory(self) -> None:
        """Choose an event directory in a dialog and load it."""
        start = self.directory_edit.text().strip() or str(Path.home())
        selected = QFileDialog.getExistingDirectory(
            self,
            "Select Receiver Function Event Directory",
            start,
        )
        if selected:
            self.directory_edit.setText(selected)
            self.load_directory(Path(selected))

    def load_from_text(self) -> None:
        """Load the directory typed in the directory box."""
        text = self.directory_edit.text().strip()
        if not text:
            QMessageBox.warning(
                self,
                "Missing Directory",
                "Please select a receiver function directory first.",
            )
            return
        self.load_directory(Path(text).expanduser())

    def load_directory(
        self,
        directory: Path,
        *,
        show_errors: bool = True,
    ) -> None:
        """Load the receiver functions of a directory that match the file pattern.

        Files are sorted by station; files that cannot be read are reported.

        :param directory: Event directory
        :type directory: pathlib.Path
        :param show_errors: Show message boxes for errors, defaults to True
        :type show_errors: bool, optional
        """
        directory = directory.resolve()
        pattern = self.pattern_edit.text().strip() or DEFAULT_PATTERN
        if not directory.is_dir():
            if show_errors:
                QMessageBox.critical(
                    self,
                    "Directory Not Found",
                    f"Could not find directory:\n{directory}",
                )
            return

        paths = [
            path
            for path in directory.glob(pattern)
            if path.is_file() and not path.name.startswith("._")
        ]
        paths.sort(
            key=lambda path: (
                natural_station_key(file_metadata(path)[1]),
                path.name,
            )
        )
        records: list[RFRecord] = []
        failures: list[str] = []
        for path in paths:
            try:
                records.append(load_rf_record(path))
            except Exception as exc:
                failures.append(f"{path.name}: {exc}")

        if not records:
            message = (
                f"No readable receiver functions found in directory:\n"
                f"{directory}\n\n"
                f"Pattern: {pattern}"
            )
            if failures:
                message += "\n\nRead errors:\n" + "\n".join(failures[:8])
            if show_errors:
                QMessageBox.warning(self, "No Waveforms", message)
            return

        self.directory_edit.setText(str(directory))
        self.records = records
        self._update_global_amplitude()
        self.selected.clear()
        self.view_start = 0
        self._populate_station_list()
        self._draw_visible_records()
        self._update_status()
        QTimer.singleShot(0, self.focus_canvas)

        if failures and show_errors:
            QMessageBox.warning(
                self,
                "Some Files Could Not Be Loaded",
                f"Loaded {len(records)} trace(s); {len(failures)} failed.\n\n"
                + "\n".join(failures[:12]),
            )

    def _populate_station_list(self) -> None:
        """Fill the station list with one checkable item per receiver function."""
        self._updating_list = True
        self.station_list.clear()
        for index, record in enumerate(self.records):
            gauss = "" if record.gauss is None else f"  F{record.gauss:.1f}"
            item = QListWidgetItem(f"{record.station}{gauss}")
            item.setFlags(
                item.flags()
                | Qt.ItemFlag.ItemIsUserCheckable
                | Qt.ItemFlag.ItemIsEnabled
            )
            item.setCheckState(Qt.CheckState.Unchecked)
            item.setData(Qt.ItemDataRole.UserRole, index)
            self.station_list.addItem(item)
        self._updating_list = False

    def _update_global_amplitude(self) -> None:
        """Set the largest absolute amplitude of all records, used to normalize every trace."""
        amplitudes = [
            float(np.max(np.abs(record.data)))
            for record in self.records
            if record.data.size
        ]
        amplitude = max(amplitudes, default=0.0)
        self.global_amplitude = (
            amplitude
            if np.isfinite(amplitude) and amplitude > 0.0
            else 1.0
        )

    def _draw_visible_records(self) -> None:
        """Draw the receiver functions of the current page."""
        self.figure.clear()
        self.axes = self.figure.add_subplot(111)
        self.artists = {}
        scale = self.scale_slider.value() / 100.0
        maximum_start = self._last_page_start()
        self.view_start = min(max(self.view_start, 0), maximum_start)
        view_end = min(len(self.records), self.view_start + ROWS_PER_VIEW)
        self.visible_indices = list(range(self.view_start, view_end))

        for local_row, record_index in enumerate(self.visible_indices):
            record = self.records[record_index]
            display_data = record.data / self.global_amplitude
            waveform = local_row - scale * display_data
            self.axes.axhline(
                local_row,
                color="#dddddd",
                linewidth=0.45,
                zorder=1,
            )
            selected = record_index in self.selected
            positive_color = SELECTED_COLOR if selected else POSITIVE_COLOR
            negative_color = SELECTED_COLOR if selected else NEGATIVE_COLOR
            positive_fill = self.axes.fill_between(
                record.times,
                local_row,
                waveform,
                where=record.data >= 0,
                interpolate=True,
                facecolor=positive_color,
                edgecolor="none",
                alpha=FILL_ALPHA,
                zorder=2,
            )
            negative_fill = self.axes.fill_between(
                record.times,
                local_row,
                waveform,
                where=record.data < 0,
                interpolate=True,
                facecolor=negative_color,
                edgecolor="none",
                alpha=FILL_ALPHA,
                zorder=2,
            )
            line, = self.axes.plot(
                record.times,
                waveform,
                color="#666666" if selected else "#303030",
                linewidth=0.55,
                alpha=0.75,
                zorder=3,
            )
            self.artists[record_index] = (
                line,
                positive_fill,
                negative_fill,
            )

        self.zero_line = self.axes.axvline(
            0.0,
            color="#b3212d",
            linestyle="--",
            linewidth=0.8,
            alpha=0.8,
            zorder=4,
        )
        visible_count = len(self.visible_indices)
        self.axes.set_ylim(ROWS_PER_VIEW - 0.5, -0.5)
        self.axes.set_yticks(range(visible_count))
        self.axes.set_yticklabels(
            [self.records[index].station for index in self.visible_indices],
            fontsize=8,
        )
        self.axes.set_xlabel("Time relative to theoretical P (s)")
        self.axes.set_ylabel("Station")
        self.axes.grid(
            True,
            axis="x",
            color="#e5e5e5",
            linewidth=0.6,
        )
        self.apply_time_range(redraw=False)
        self.canvas.draw_idle()
        self._update_status()

    def apply_time_range(self, *, redraw: bool = True) -> None:
        """Apply the time range of the spin boxes to the axes.

        :param redraw: Redraw the canvas, defaults to True
        :type redraw: bool, optional
        """
        if not hasattr(self, "axes"):
            return
        xmin = self.xmin_spin.value()
        xmax = self.xmax_spin.value()
        if xmin >= xmax:
            QMessageBox.warning(
                self,
                "Invalid Time Range",
                "The start time must be earlier than the end time.",
            )
            return
        self.axes.set_xlim(xmin, xmax)
        if redraw:
            self.canvas.draw_idle()

    def show_full_time_range(self) -> None:
        """Show the full time span of all records."""
        if not self.records:
            return
        xmin = min(float(record.times[0]) for record in self.records)
        xmax = max(float(record.times[-1]) for record in self.records)
        self.xmin_spin.setValue(xmin)
        self.xmax_spin.setValue(xmax)
        self.apply_time_range()

    def update_scale(self) -> None:
        """Redraw with the amplitude scale of the slider."""
        if not self.records:
            return
        self._draw_visible_records()

    def on_canvas_click(self, event) -> None:
        """Toggle the mark of the waveform under a left click.

        :param event: Mouse click event
        :type event: matplotlib.backend_bases.MouseEvent
        """
        self.focus_canvas()
        if (
            not self.records
            or event.inaxes is not getattr(self, "axes", None)
            or event.ydata is None
            or event.button != 1
        ):
            return
        local_row = int(round(event.ydata))
        if (
            0 <= local_row < len(self.visible_indices)
            and abs(event.ydata - local_row) <= 0.46
        ):
            index = self.visible_indices[local_row]
            self.set_selected(index, index not in self.selected)

    def _last_page_start(self) -> int:
        """Index of the first record on the last page.

        :rtype: int
        """
        if not self.records:
            return 0
        return ((len(self.records) - 1) // ROWS_PER_VIEW) * ROWS_PER_VIEW

    def change_page(self, direction: int) -> None:
        """Move one page forward or backward.

        :param direction: Positive for the next page, otherwise the previous page
        :type direction: int
        """
        if not self.records:
            return
        step = ROWS_PER_VIEW if direction > 0 else -ROWS_PER_VIEW
        new_start = min(
            max(self.view_start + step, 0),
            self._last_page_start(),
        )
        if new_start == self.view_start:
            return
        self.view_start = new_start
        self._draw_visible_records()
        if self.station_list.count():
            self.station_list.scrollToItem(
                self.station_list.item(self.view_start)
            )

    def eventFilter(self, watched, event) -> bool:
        """Handle the ``z`` and ``c`` page keys anywhere in the window, except in text fields.

        :param watched: Object receiving the event
        :type watched: PySide6.QtCore.QObject
        :param event: Event to filter
        :type event: PySide6.QtCore.QEvent
        :return: True if the key was handled
        :rtype: bool
        """
        if (
            event.type() == QEvent.Type.KeyPress
            and self.isActiveWindow()
            and not isinstance(
                QApplication.focusWidget(),
                (QLineEdit, QDoubleSpinBox),
            )
        ):
            if event.key() == Qt.Key.Key_Z:
                self.change_page(-1)
                return True
            if event.key() == Qt.Key.Key_C:
                self.change_page(1)
                return True
        return super().eventFilter(watched, event)

    def on_list_item_changed(self, item: QListWidgetItem) -> None:
        """Mark or unmark a record when its station is checked or unchecked.

        :param item: Changed list item
        :type item: PySide6.QtWidgets.QListWidgetItem
        """
        if self._updating_list:
            return
        index = int(item.data(Qt.ItemDataRole.UserRole))
        checked = item.checkState() == Qt.CheckState.Checked
        self.set_selected(index, checked, update_list=False)

    def set_selected(
        self,
        index: int,
        selected: bool,
        *,
        update_list: bool = True,
        redraw: bool = True,
    ) -> None:
        """Mark or unmark a record and update its colors and list item.

        :param index: Record index
        :type index: int
        :param selected: True to mark the record for deletion
        :type selected: bool
        :param update_list: Update the check box of the list item, defaults to True
        :type update_list: bool, optional
        :param redraw: Redraw the canvas, defaults to True
        :type redraw: bool, optional
        """
        if selected:
            self.selected.add(index)
        else:
            self.selected.discard(index)

        if index in self.artists:
            line, positive_fill, negative_fill = self.artists[index]
            line.set_color("#666666" if selected else "#303030")
            line.set_linewidth(0.7 if selected else 0.55)
            positive_fill.set_facecolor(
                SELECTED_COLOR if selected else POSITIVE_COLOR
            )
            negative_fill.set_facecolor(
                SELECTED_COLOR if selected else NEGATIVE_COLOR
            )
            positive_fill.set_alpha(FILL_ALPHA)
            negative_fill.set_alpha(FILL_ALPHA)

        if 0 <= index < self.station_list.count():
            was_updating = self._updating_list
            self._updating_list = True
            item = self.station_list.item(index)
            if update_list:
                item.setCheckState(
                    Qt.CheckState.Checked
                    if selected
                    else Qt.CheckState.Unchecked
                )
            item.setForeground(
                QColor("#777777") if selected else QColor("#202020")
            )
            self._updating_list = was_updating

        self._update_status()
        if redraw:
            self.canvas.draw_idle()

    def select_all(self) -> None:
        """Mark all records."""
        for index in range(len(self.records)):
            self.set_selected(index, True, redraw=False)
        self.canvas.draw_idle()

    def clear_selection(self) -> None:
        """Unmark all records."""
        for index in range(len(self.records)):
            self.set_selected(index, False, redraw=False)
        self.canvas.draw_idle()

    def invert_selection(self) -> None:
        """Invert the marks of all records."""
        previous = set(self.selected)
        for index in range(len(self.records)):
            self.set_selected(
                index,
                index not in previous,
                redraw=False,
            )
        self.canvas.draw_idle()

    def delete_selected_files(self) -> None:
        """Permanently delete the SAC files of the marked records after confirmation.

        macOS ``._`` sidecar files are removed too, and the view is refreshed.
        """
        if not self.selected:
            QMessageBox.information(
                self,
                "No Waveforms Selected",
                "Click a waveform or check a station first.",
            )
            return

        selected_indices = sorted(self.selected)
        selected_paths = [self.records[index].path for index in selected_indices]
        preview = "\n".join(path.name for path in selected_paths[:12])
        if len(selected_paths) > 12:
            preview += f"\n...and {len(selected_paths) - 12} more file(s)"
        reply = QMessageBox.warning(
            self,
            "Permanently Delete Original SAC Files",
            f"This will permanently delete {len(selected_paths)} original "
            "SAC file(s). This action cannot be undone:\n\n"
            f"{preview}\n\nContinue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        deleted_indices: set[int] = set()
        failures: list[str] = []
        for index, path in zip(selected_indices, selected_paths):
            try:
                path.unlink()
            except FileNotFoundError:
                pass
            except OSError as exc:
                failures.append(f"{path.name}: {exc}")
                continue

            deleted_indices.add(index)
            sidecar = path.with_name(f"._{path.name}")
            try:
                sidecar.unlink()
            except FileNotFoundError:
                pass
            except OSError as exc:
                failures.append(f"{sidecar.name}: {exc}")

        self.records = [
            record
            for index, record in enumerate(self.records)
            if index not in deleted_indices
        ]
        self._update_global_amplitude()
        self.selected.clear()
        self.view_start = min(
            self.view_start,
            self._last_page_start(),
        )
        self._populate_station_list()
        if self.records:
            self._draw_visible_records()
        else:
            self.figure.clear()
            axes = self.figure.add_subplot(111)
            axes.axis("off")
            axes.text(
                0.5,
                0.5,
                "No receiver functions remain in this directory",
                ha="center",
                va="center",
                transform=axes.transAxes,
                fontsize=15,
            )
            self.visible_indices = []
            self.artists = {}
            self.canvas.draw_idle()
        self._update_status()

        deleted_count = len(deleted_indices)
        if failures:
            QMessageBox.warning(
                self,
                "Deletion Partially Completed",
                f"Deleted {deleted_count} SAC file(s); "
                f"{len(failures)} error(s) occurred:\n\n"
                + "\n".join(failures[:12]),
            )
        else:
            self.statusBar().showMessage(
                f"Permanently deleted {deleted_count} original SAC file(s)",
                8000,
            )

    def _update_status(self) -> None:
        """Update the page buttons and the status text."""
        self.previous_page_button.setEnabled(
            bool(self.records) and self.view_start > 0
        )
        self.next_page_button.setEnabled(
            bool(self.records) and self.view_start < self._last_page_start()
        )
        if self.visible_indices:
            visible_text = (
                f"Showing {self.visible_indices[0] + 1}–"
                f"{self.visible_indices[-1] + 1}"
            )
        else:
            visible_text = "Showing 0"
        self.status_label.setText(
            f"Total: {len(self.records)} | {visible_text} | "
            f"Marked for deletion: {len(self.selected)} | "
            "Gray = marked for deletion"
        )


def parse_args() -> argparse.Namespace:
    """Parse the command-line arguments of ``fwat_pick_rf``.

    :rtype: argparse.Namespace
    """
    parser = argparse.ArgumentParser(
        description="Open the PySide6 receiver-function review/delete GUI."
    )
    parser.add_argument(
        "directory",
        nargs="?",
        type=Path,
        help="Optional event directory containing RF SAC files.",
    )
    return parser.parse_args()


def main() -> None:
    """Command-line entry point of ``fwat_pick_rf``."""
    args = parse_args()
    application = QApplication(sys.argv[:1])
    window = RFPickerWindow(args.directory)
    window.show()
    raise SystemExit(application.exec())


if __name__ == "__main__":
    main()
