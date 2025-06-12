
from typing import TYPE_CHECKING

from qtpy.QtWidgets import QVBoxLayout, QPushButton, QWidget, QLabel, QProgressBar
from napari_file2folder._custom_widgets import HoverTooltipButton
from magicgui.widgets import (
    CheckBox,
    ComboBox,
    Container,
    EmptyWidget,
    Label,
    create_widget,
    PushButton,
)
import os
import tifffile
from bioio import BioImage
import zarr
from pathlib import Path
import napari


class File2FolderWidget(QWidget):

    def __init__(self, viewer: "napari.viewer.Viewer"):
        super().__init__()

        self._viewer = viewer

        self._array_file_path = create_widget(
            widget_type="FileEdit",
            label="Array file",
            options={"mode": "r"},
        )
        
        self._array_file_path.changed.connect(self._update_dimensions)
        self._array_file_path.changed.connect(self._update_dimension_choices)

        self._array_file_path.label_changed.connect(self._update_dimensions)
        self._array_file_path.label_changed.connect(self._update_dimension_choices)


        self._refresh_button = create_widget(
            widget_type="PushButton",
            label="Refresh",
        )

        refresh_container = Container(
            widgets=[self._refresh_button],
            labels=False,
            layout="horizontal",
        )

        self._add_tooltip_button_to_container(
            refresh_container, "Refresh the dimensions"
        )

        self._refresh_button.native.clicked.connect(self._update_dimensions)

        self._default_shape_text = f"Shape: <a style=color:#D41159;>None</a>"
        self._shape_text = QLabel(self._default_shape_text)

        self._dimension_choice_combo = create_widget(
            widget_type="ComboBox",
            options={"nullable": False}
        )

        dimension_choice_container = Container(
            widgets=[self._dimension_choice_combo],
            labels=False,
            layout="horizontal",
        )

        self._add_tooltip_button_to_container(
            dimension_choice_container,
            "Choose dimension along which to either\n" 
            "    (i) select the element at the midpoint along the dimension (e.g for inspection)\n"
            "or (ii) save each element as a separate tif file in the provided folder"
        )

        self._load_middle_element_button = create_widget(
            widget_type="PushButton",
            label="Load middle element in Napari",
        )

        self._load_middle_element_button.clicked.connect(
            self._load_middle_element
        )

        middle_elem_button_container = Container(
            widgets=[self._load_middle_element_button],
            labels=False,
            layout="horizontal",
        )

        self._add_tooltip_button_to_container(
            middle_elem_button_container,
            (
                "Load middle element as Napari layer,\n"
                "e.g to check if dimensions match your expectations"
            )
        )

        ###
        self._save_to_folder_path = create_widget(
            widget_type="FileEdit",
            label="Folder path",
            options={"mode": "d"},
        )
        ###

        self._save_to_folder_compress_checkbox = create_widget(
            widget_type="CheckBox",
            label="Compress when saving",
            options={"value": False},
        )

        self._save_to_folder_button = create_widget(
            widget_type="PushButton",
            label="Save elements along dimension to folder",
        )

        self._save_to_folder_button.clicked.connect(
            self._save_to_folder
        )

        save_to_folder_container = Container(
            widgets=[self._save_to_folder_button],
            labels=False,
            layout="horizontal",
        )

        self._add_tooltip_button_to_container(
            save_to_folder_container,
            (
                "Save all elements of the specified dimension\n"
                "independently to a folder as tifs."
            )
        )

        self._progress_bar = QProgressBar()


        self.setLayout(QVBoxLayout())


        # self.layout().addWidget(self._array_layer_combo.native)
        self.layout().addWidget(QLabel("<u>Select path to bioimage:</u>"))
        self.layout().addWidget(self._array_file_path.native)
        self.layout().addWidget(refresh_container.native)
        self.layout().addWidget(QLabel(f"Dimensions of currently selected layer:"))
        self.layout().addWidget(self._shape_text)
        self.layout().addWidget(QLabel(""))

        self.layout().addWidget(QLabel("<u>Select dimension:</u>"))
        self.layout().addWidget(dimension_choice_container.native)
        self.layout().addWidget(QLabel(""))

        self.layout().addWidget(QLabel("<u>(optional) Inspect middle element:</u>"))
        self.layout().addWidget(middle_elem_button_container.native)
        self.layout().addWidget(QLabel(""))

        self.layout().addWidget(QLabel("<u>Select path where the folder will be created:</u>"))
        # self.layout().addWidget(QLabel(f"Path at which to create folder for saving:"))
        self.layout().addWidget(self._save_to_folder_path.native)
        self.layout().addWidget(self._save_to_folder_compress_checkbox.native)
        self.layout().addWidget(save_to_folder_container.native)
        self.layout().addWidget(self._progress_bar)
        
        # self._update_layer_combos()
        self._update_dimensions()
        self._update_dimension_choices()
        
        self.layout().addStretch(1)

    def _coerce_path(self, path, type):
        path = str(path)
        if path.startswith('file:'):
            path = path[5:].strip()
        if type == "folder":
            return Path(path), path != "." and os.path.isdir(path)
        elif type == "file":
            return Path(path), path != "." and os.path.isfile(path)
        else:
            raise NotImplementedError

    def _save_to_folder(self):
        save_path, save_path_valid = self._coerce_path(self._save_to_folder_path.value, "folder")
        if save_path_valid:
            path, path_valid = self._coerce_path(self._array_file_path.value, "file")
            if path_valid:

                dimension_index, dimension_shape = self._dimension_index_from_str(
                    self._dimension_choice_combo.value
                )

                path_to_folder = f"{save_path}/{path.stem}_dim{dimension_index}"
                self._create_folder_if_needed(path_to_folder)

                compress_params = {}
                if self._save_to_folder_compress_checkbox.value:
                    compress_params.update({"compression": ("zlib", 1)})

                self._lazy_save_slices(
                    slice_dim=dimension_index,
                    file=str(path),
                    path_to_save=path_to_folder,
                    compress_args=compress_params
                )

                self._progress_bar.reset()

                napari.utils.notifications.show_info(
                    f"Finished saving files!\n"
                    f"Saved to {path_to_folder}"
                )



    def _create_folder_if_needed(self, folder_path):
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
    
    def _update_dimension_choices(self):
        path, path_valid = self._coerce_path(self._array_file_path.value, "file")
        if path_valid:
            shape = self._lazy_shape(path)
            dimensions_as_str = [f"dim {i} ({s})" for i,s in enumerate(shape)]
            self._dimension_choice_combo.choices = dimensions_as_str
        else:
            self._dimension_choice_combo.choices = ["None"]

    def _dimension_index_from_str(self, string):
        dim_index = int(string.split(' ')[1])
        dim_shape = int(string.split(' ')[2][1:-1])

        return dim_index, dim_shape

    def _load_middle_element(self):
        path, path_valid = self._coerce_path(self._array_file_path.value, "file")
        if path_valid:
            dimension_index, dimension_shape = self._dimension_index_from_str(
                self._dimension_choice_combo.value
            )

            middle_slice = self._lazy_grab_slice(
                element_index=int(dimension_shape/2),
                slice_dim=dimension_index,
                file=str(path)
            )
            if middle_slice is None:
                napari.utils.notifications.show_warning(
                    "Please choose a compatible TIF file"
                )
            else:
                self._viewer.add_image(middle_slice)
        else:
            napari.utils.notifications.show_warning(
                "Please choose a compatible TIF file"
            )

    
    def _lazy_save_slices(self, slice_dim: int, file: str, path_to_save: str,
                              compress_args: dict = {}):
        """
        Lazily slice a multidimensional file along a specified dimension.

        Parameters: 
        - file: path to the image file.
        - slice_dim: the dimension (axis) along which to slice.
        - path_to_save: path to the folder where to save the slices.
        - compress_args: dictionary of arguments to pass to tifffile.imwrite.
        
        Returns:
        - The element of the sliced array at the specified index.
        """

        file = str(file)
        if file.endswith(".tif") or file.endswith(".tiff") or file.endswith("lsm"):
            with tifffile.TiffFile(file) as tif:
                shape = tif.series[0].shape
                
                slices = [slice(None) for _ in range(len(shape))]

                zarr_store = tif.series[0].aszarr()
                zarr_array = zarr.open(zarr_store)

                for element_index in range(shape[slice_dim]):
                    slices[slice_dim] = element_index
                    
                    stack = zarr_array[tuple(slices)]

                    name_tif = file.split(os.sep)[-1].split('.')[0]

                    tifffile.imwrite(
                        f"{path_to_save}/{name_tif}_slice{element_index:03d}.tif",
                        stack,
                        **compress_args
                    )

                    self._progress_bar.setValue(
                        int((element_index+1)/shape[slice_dim]*100)
                    )
        else:
            img = BioImage(file)
            shape = tuple([elem for elem in img.shape if elem != 1])
            lazy_array = img.dask_data.reshape(shape)   

                
            slices = [slice(None) for _ in range(len(shape))]

            for element_index in range(shape[slice_dim]):
                slices[slice_dim] = element_index
                
                stack = lazy_array[tuple(slices)].compute()

                name_tif = file.split(os.sep)[-1].split('.')[0]

                tifffile.imwrite(
                    f"{path_to_save}/{name_tif}_slice{element_index:03d}.tif",
                    stack,
                    **compress_args
                )

                self._progress_bar.setValue(
                    int((element_index+1)/shape[slice_dim]*100)
                )

                



    def _lazy_grab_slice(self, slice_dim, file, element_index: int = None):
        """
        Lazily slice a multidimensional file along a specified dimension.

        Parameters:
        - file: path to the image file.
        - slice_dim: the dimension (axis) along which to slice.
        - element_index: the index of the element to retrieve along the slice dimension.
        
        Returns:
        - The element of the sliced array at the specified index.
        """
        
        file = str(file)
        if file.endswith(".tif") or file.endswith(".tiff") or file.endswith("lsm"):
            with tifffile.TiffFile(file) as tif:
                shape = tif.series[0].shape
                slices = [slice(None) for _ in range(len(shape))]
                zarr_array = zarr.open(tif.series[0].aszarr())
                slices[slice_dim] = element_index
                stack = zarr_array[tuple(slices)]
                
        else:
            img = BioImage(file)
            shape = tuple([elem for elem in img.shape if elem != 1])
            lazy_array = img.dask_data.reshape(shape)
            
            slices = [slice(None) for _ in range(len(shape))]

            slices[slice_dim] = element_index

            stack = lazy_array[tuple(slices)].compute()

        return stack


    def _lazy_shape(self, file):
        """
        Lazily retrieve the shape of a multidimensional file.

        Parameters:
        - file: path to the image file.

        Returns:
        - The shape of the image file.
        """
        file = str(file)
        if file.endswith(".tif") or file.endswith(".tiff") or file.endswith("lsm"):
            with tifffile.TiffFile(file) as tif:
                shape = tif.series[0].shape
        else:
            img = BioImage(file)
            shape = tuple([elem for elem in img.shape if elem != 1])

        return shape

    def _update_dimensions(self):
        path, path_valid = self._coerce_path(self._array_file_path.value, "file")

        if path_valid:
            shape = self._lazy_shape(path)

            self._shape_text.setText(f"Shape: <a style=color:#1A85FF;>{shape}</a>")
        else:
            self._shape_text.setText(self._default_shape_text)

    def _bind_layer_combo(self, obj):
        """
        This used so that when calling layer_combo.value, we get the layer object,
        not the name of the layer
        """
        name = obj.native.currentText()
        if name not in ("", "-----"):
            return self._viewer.layers[name]
        else:
            return None
        
    def _update_layer_combos(self):

        ### 1. Clear all combos but keep the previous choice if possible
        previous_text = self._array_layer_combo.native.currentText()
        self._array_layer_combo.native.clear()

        ### 2. Add layers to combos
        # add layers to compatible combos
        for layer in self._viewer.layers:
            if (
                isinstance(layer, napari.layers.Image | napari.layers.Labels)
                and self._array_layer_combo.enabled
            ):
                self._array_layer_combo.native.addItem(layer.name)

        ### 3. Reset combo current choice to previous text if possible
        all_choices = [
            self._array_layer_combo.native.itemText(i) for i in range(self._array_layer_combo.native.count())
        ]
        if previous_text in all_choices:

            # if the previous layer is None, set it to the newest layer
            if previous_text == self._array_layer_combo.native.itemText(0):
                self._array_layer_combo.native.setCurrentIndex(self._array_layer_combo.native.count() - 1)
            else:
                self._array_layer_combo.native.setCurrentText(previous_text)
        else:
            self._array_layer_combo.native.setCurrentIndex(0)

    def _add_tooltip_button_to_container(self, container, tooltip_text):
        button = HoverTooltipButton(tooltip_text)
        button.native = button
        button._explicitly_hidden = False
        button.name = ""

        if isinstance(container, Container):
            container.append(button)
        else:
            if isinstance(container, CheckBox | PushButton):
                container = Container(
                    widgets=[container, button],
                    labels=False,
                    layout="horizontal",
                )
            else:
                container_label = container.label
                container.label = ""
                container = Container(
                    widgets=[Label(value=container_label), container, button],
                    labels=False,
                    layout="horizontal",
                )
            return container
        return None


if __name__ == "__main__":
    import napari

    viewer = napari.Viewer()
    widget = File2FolderWidget(viewer)
    viewer.window.add_dock_widget(widget)

    napari.run()
