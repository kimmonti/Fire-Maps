import os
import re
from qgis.core import (
    QgsProject,
    QgsPrintLayout,
    QgsLayoutExporter,
    QgsLayoutItemMap,
    QgsLayoutItemLegend,
    QgsLayoutItemLabel,
    QgsLayerTree,
    QgsReadWriteContext,
    QgsRasterLayer
)
from PyQt5.QtXml import QDomDocument

def extract_month_year_kernel(layer_name):
    match = re.search(r'Densidad Kernel (\d{2})_(\d{4})', layer_name)
    if match:
        month = int(match.group(1))
        year = match.group(2)
        month_name = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                      "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        return month_name[month - 1], year, f"{match.group(1)}/{year}"
    return None, None, None

def update_label_text(item, date_emission):
    original_text = item.text()
    if "Fecha de emision:" in original_text:
        new_text = re.sub(r"Fecha de emision: \d{2}/\d{4}", f"Fecha de emision: {date_emission}", original_text)
        item.setText(new_text)
        print(f"Etiqueta actualizada: {new_text}")

def create_and_export_kernel_maps():
    project = QgsProject.instance()
    template_path = 'C:/carmen/MAPA KERNEL.qpt'

    raster_layers = [layer for layer in project.mapLayers().values() if isinstance(layer, QgsRasterLayer)]

    if not raster_layers:
        print("No se encontraron capas raster en el proyecto.")
        return

    desired_scale = 600000

    for raster_layer in raster_layers:
        layout = QgsPrintLayout(project)
        layout.initializeDefaults()

        try:
            with open(template_path, 'rt') as f:
                template_content = f.read()
        except Exception as e:
            print(f"Error al leer la plantilla: {e}")
            continue

        doc = QDomDocument()
        doc.setContent(template_content)
        layout.loadFromTemplate(doc, QgsReadWriteContext())

        month_name, year, date_emission = extract_month_year_kernel(raster_layer.name())
        if month_name and year:
            for item in layout.items():
                if isinstance(item, QgsLayoutItemLabel):
                    current_text = item.text()
                    if "Densidad de Kernel" in current_text:
                        new_text = f"Densidad de Kernel\n{month_name} {year}"
                        item.setText(new_text)
                        print(f"Título actualizado a: {new_text}")
                    elif "Fecha de emision:" in current_text:
                        update_label_text(item, date_emission)

        map_item = None
        legend_item = None
        for item in layout.items():
            if isinstance(item, QgsLayoutItemMap):
                map_item = item
            elif isinstance(item, QgsLayoutItemLegend):
                legend_item = item

        if map_item is None:
            print("No se encontró ningún elemento de mapa en la plantilla.")
            continue

        # Centrar el contenido dentro del visor
        original_extent = map_item.extent()
        map_item.setLayers([raster_layer])
        raster_extent = raster_layer.extent()

        map_ratio = map_item.rect().width() / map_item.rect().height()
        layer_ratio = raster_extent.width() / raster_extent.height()

        centered_extent = raster_extent
        if map_ratio > layer_ratio:
            new_width = raster_extent.height() * map_ratio
            diff_width = new_width - raster_extent.width()
            centered_extent.setXMinimum(raster_extent.xMinimum() - diff_width / 2)
            centered_extent.setXMaximum(raster_extent.xMaximum() + diff_width / 2)
        else:
            new_height = raster_extent.width() / map_ratio
            diff_height = new_height - raster_extent.height()
            centered_extent.setYMinimum(raster_extent.yMinimum() - diff_height / 2)
            centered_extent.setYMaximum(raster_extent.yMaximum() + diff_height / 2)

        # Ajustar la extensión del mapa al área centrada
        map_item.setExtent(centered_extent)

        # Configurar la escala deseada
        map_item.setScale(desired_scale)

        if legend_item:
            legend_tree = QgsLayerTree()
            legend_tree.addLayer(raster_layer)
            legend_item.model().setRootGroup(legend_tree)
            legend_item.refresh()

        raster_path = raster_layer.dataProvider().dataSourceUri()
        output_folder = os.path.dirname(raster_path)
        output_png = os.path.join(output_folder, f'mapa_{raster_layer.name()}.png')

        exporter = QgsLayoutExporter(layout)
        result = exporter.exportToImage(output_png, QgsLayoutExporter.ImageExportSettings())

        if result == QgsLayoutExporter.Success:
            print(f"Mapa exportado exitosamente a: {output_png}")
        else:
            print("Error al exportar el mapa.")

# Ejecutar la función
create_and_export_kernel_maps()
