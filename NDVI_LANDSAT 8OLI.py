import os
import numpy as np
from osgeo import gdal
from qgis.core import (
    QgsProject,
    QgsRasterLayer,
    QgsSingleBandPseudoColorRenderer,
    QgsColorRampShader,
    QgsRasterShader
)
from PyQt5.QtGui import QColor

# Parámetros de entrada
base_directory = r"D:\KIM_USER\Tesis\FINALES\MAPAS_LST_LANDSAT 8 OLI"

def add_layer_to_project(path, name):
    """Añade una capa raster al proyecto QGIS."""
    layer = QgsRasterLayer(path, name)
    if layer.isValid():
        QgsProject.instance().addMapLayer(layer)
        return layer
    else:
        print(f"Error al cargar la capa {name}")
        return None

def calculate_ndvi(band4_path, band5_path, output_path):
    """Calcula el NDVI utilizando GDAL y guarda el resultado."""
    band4_ds = gdal.Open(band4_path)
    band5_ds = gdal.Open(band5_path)
    
    band4 = band4_ds.GetRasterBand(1).ReadAsArray().astype(float)
    band5 = band5_ds.GetRasterBand(1).ReadAsArray().astype(float)

    ndvi = (band5 - band4) / (band5 + band4)
    ndvi[np.isnan(ndvi)] = 0

    driver = gdal.GetDriverByName('GTiff')
    out_ds = driver.Create(output_path, band4_ds.RasterXSize, band4_ds.RasterYSize, 1, gdal.GDT_Float32)
    out_ds.SetGeoTransform(band4_ds.GetGeoTransform())
    out_ds.SetProjection(band4_ds.GetProjection())
    
    out_band = out_ds.GetRasterBand(1)
    out_band.WriteArray(ndvi)
    out_band.SetNoDataValue(-9999)
    out_band.FlushCache()
    
    band4_ds = None
    band5_ds = None
    out_ds = None

def apply_simple_color_ramp(layer):
    """Aplica una rampa de colores verde simple al raster NDVI con 4 clases."""
    if layer.isValid():
        provider = layer.dataProvider()

        # Crear una lista de colores para las clases (tonos de azul)
        color_mapping = [
            QgsColorRampShader.ColorRampItem(-1, QColor(0, 0, 128), "-1"),    # Azul oscuro
            QgsColorRampShader.ColorRampItem(0, QColor(128, 128, 128), "0"),    # Gris
            QgsColorRampShader.ColorRampItem(0.5, QColor(60, 179, 113), "0.5"), # Verde claro
            QgsColorRampShader.ColorRampItem(1, QColor(0, 100, 0), "1")   # Verde oscuro
        ]

        # Crear un shader de rampa de colores
        color_ramp_shader = QgsColorRampShader()
        color_ramp_shader.setColorRampType(QgsColorRampShader.Interpolated)  # Modo interpolado
        color_ramp_shader.setColorRampItemList(color_mapping)

        raster_shader = QgsRasterShader()
        raster_shader.setRasterShaderFunction(color_ramp_shader)

        # Crear un renderizador de pseudocolor monobanda
        renderer = QgsSingleBandPseudoColorRenderer(layer.dataProvider(), 1, raster_shader)

        layer.setRenderer(renderer)
        layer.triggerRepaint()
    else:
        print("Error: La capa no es válida para aplicar la simbología.")

def process_landsat_data(year_folder):
    """Procesa los datos Landsat para cada carpeta de fecha."""
    for date_folder in os.listdir(year_folder):
        date_path = os.path.join(year_folder, date_folder)
        if os.path.isdir(date_path):
            # Definir las rutas de las bandas
            band_4_path = os.path.join(date_path, "B4.tif")
            band_5_path = os.path.join(date_path, "B5.tif")

            # Verificar si las bandas existen
            if not (os.path.exists(band_4_path) and os.path.exists(band_5_path)):
                print(f"Faltan algunas bandas en {date_path}.")
                continue

            # Calcular NDVI
            ndvi_path = os.path.join(date_path, f"NDVI_{date_folder}.tif")
            calculate_ndvi(band_4_path, band_5_path, ndvi_path)
            ndvi_layer = add_layer_to_project(ndvi_path, f"NDVI_{date_folder}")
            # Aplicar la rampa de colores
            if ndvi_layer:
                apply_simple_color_ramp(ndvi_layer)

def main():
    """Función principal para procesar todos los datos Landsat."""
    for year_folder in os.listdir(base_directory):
        year_path = os.path.join(base_directory, year_folder)
        if os.path.isdir(year_path):
            process_landsat_data(year_path)

# Ejecutar el proceso
main()
