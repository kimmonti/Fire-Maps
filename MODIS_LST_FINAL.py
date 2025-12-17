import os
from osgeo import gdal
from qgis.core import (
    QgsProject, QgsRasterLayer, QgsColorRampShader, QgsRasterShader, QgsSingleBandPseudoColorRenderer,
    QgsPrintLayout, QgsLayoutItemMap, QgsLayoutItemLabel, QgsLayoutItemLegend, QgsLayoutExporter
)
from PyQt5.QtGui import QColor, QFont
from pathlib import Path

# Ruta base de MODIS_TERRA
base_dir = r"E:/carmen_power/MODIS_TERRA"
mask_shp = r"E:/CARMEN/BENJAMIN ACEVAL.shp"

# EPSG de salida
epsg_code = "EPSG:32721"

# Recorrer cada año y mes en la estructura de carpetas
for year in ["2012", "2014", "2016", "2018", "2020", "2022"]:
    year_path = os.path.join(base_dir, year)
    for month in range(1, 13):
        month_folder = f"{month:02d}_{year}"
        month_path = os.path.join(year_path, month_folder)
        
        if not os.path.exists(month_path):
            continue
        
        hdf_files = [f for f in os.listdir(month_path) if f.endswith(".hdf")]
        for hdf_file in hdf_files:
            hdf_path = os.path.join(month_path, hdf_file)
            out_dir = os.path.join(month_path, "Reproyectado")
            lst_dir = os.path.join(month_path, "LST")
            os.makedirs(out_dir, exist_ok=True)
            os.makedirs(lst_dir, exist_ok=True)
            
            hdf_dataset = gdal.Open(hdf_path, gdal.GA_ReadOnly)
            subdatasets = hdf_dataset.GetSubDatasets()
            
            lst_raster = None
            for subdataset, desc in subdatasets:
                name = desc.split(':')[-1]
                output_tif = os.path.join(out_dir, f"{name}.tif")
                
                gdal.Warp(output_tif, subdataset, dstSRS=epsg_code, resampleAlg=gdal.GRA_Bilinear)
                
                if "LST_Day_1km" in name:
                    lst_raster = output_tif
            
            if lst_raster:
                lst_output = os.path.join(lst_dir, f"LST_{month_folder}.tif")
                gdal.Translate(lst_output, lst_raster, outputType=gdal.GDT_Float32, scaleParams=[[7500, 13000, 27, 70]])
                
                lst_clip_output = os.path.join(lst_dir, f"LST_{month_folder}_BENJAMIN_ACEVAL.tif")
                gdal.Warp(lst_clip_output, lst_output, cutlineDSName=mask_shp, cropToCutline=True)
                
                raster_layer = QgsRasterLayer(lst_clip_output, f"LST_{month_folder}_BENJAMIN_ACEVAL")
                if raster_layer.isValid():
                    provider = raster_layer.dataProvider()
                    stats = provider.bandStatistics(1, QgsRasterBandStats.All)
                    min_value = stats.minimumValue
                    max_value = stats.maximumValue
                    
                    shader = QgsColorRampShader()
                    shader.setColorRampType(QgsColorRampShader.Interpolated)
                    shader.setColorRampItemList([
                        QgsColorRampShader.ColorRampItem(min_value, QColor(255, 255, 0), f"{min_value:.2f}°C"),
                        QgsColorRampShader.ColorRampItem(min_value + (max_value - min_value) * 0.33, QColor(255, 165, 0), f"{(min_value + (max_value - min_value) * 0.33):.2f}°C"),
                        QgsColorRampShader.ColorRampItem(min_value + (max_value - min_value) * 0.66, QColor(255, 69, 0), f"{(min_value + (max_value - min_value) * 0.66):.2f}°C"),
                        QgsColorRampShader.ColorRampItem(max_value, QColor(153, 0, 0), f"{max_value:.2f}°C")
                    ])
                    
                    raster_shader = QgsRasterShader()
                    raster_shader.setRasterShaderFunction(shader)
                    renderer = QgsSingleBandPseudoColorRenderer(raster_layer.dataProvider(), 1, raster_shader)
                    raster_layer.setRenderer(renderer)
                    raster_layer.triggerRepaint()
                    
                    QgsProject.instance().addMapLayer(raster_layer)
                    print(f"LST {month_folder} agregado a QGIS con simbología corregida y en °C.")
                    
                    # Generar mapa y exportar como PNG en el mismo directorio del raster
                    project = QgsProject.instance()
                    layout = QgsPrintLayout(project)
                    layout.initializeDefaults()
                    project.layoutManager().addLayout(layout)
                    
                    map_item = QgsLayoutItemMap(layout)
                    map_item.setRect(20, 20, 150, 100)
                    layout.addLayoutItem(map_item)
                    
                    map_item.setLayers([raster_layer])
                    map_item.setExtent(raster_layer.extent())
                    
                    title_item = QgsLayoutItemLabel(layout)
                    title_item.setText(f"LST - {month_folder}")
                    title_item.setFont(QFont("Arial", 16))
                    title_item.setPos(20, 10)
                    layout.addLayoutItem(title_item)
                    
                    legend_item = QgsLayoutItemLegend(layout)
                    legend_item.setTitle("Leyenda")
                    legend_item.setLinkedMap(map_item)
                    legend_item.setPos(160, 20)
                    layout.addLayoutItem(legend_item)
                    
                    output_png_path = os.path.join(lst_dir, f"LST_{month_folder}.png")
                    exporter = QgsLayoutExporter(layout)
                    result = exporter.exportToImage(output_png_path, QgsLayoutExporter.ImageExportSettings())
                    
                    if result == QgsLayoutExporter.Success:
                        print(f"Mapa guardado en: {output_png_path}")
                    else:
                        print("Error al guardar el mapa.")
                else:
                    print(f"Error: No se pudo cargar la capa {month_folder} en QGIS.")
            else:
                print(f"Error: No se encontró la capa LST_Day_1km en {hdf_file}.")
