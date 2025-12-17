import os
import numpy as np
from osgeo import gdal
from qgis.core import QgsProject, QgsRasterLayer, QgsSingleBandPseudoColorRenderer, QgsColorRampShader, QgsRasterShader
from qgis.utils import iface
from PyQt5.QtGui import QColor

# Parámetros de entrada
base_directory = r"D:\KIM_USER\Tesis\LANDSAT 8 OLI"

def add_layer_to_project(path, name):
    """Añade una capa raster al proyecto QGIS."""
    layer = QgsRasterLayer(path, name)
    if layer.isValid():
        QgsProject.instance().addMapLayer(layer)
        return layer
    else:
        print(f"Error al cargar la capa {name}")
        return None

def calculate_lst_gdal(band3_path, band4_path, band6_path, output_path):
    """Calcula la LST utilizando GDAL y guarda el resultado."""
    # Abrir las bandas usando GDAL
    band3_ds = gdal.Open(band3_path)
    band4_ds = gdal.Open(band4_path)
    band6_ds = gdal.Open(band6_path)
    
    # Leer los datos de las bandas
    band3 = band3_ds.GetRasterBand(1).ReadAsArray().astype(float)
    band4 = band4_ds.GetRasterBand(1).ReadAsArray().astype(float)
    band6 = band6_ds.GetRasterBand(1).ReadAsArray().astype(float)

    # Parámetros de radiancia
    ML = 0.067087
    AL = -0.06709
    K1 = 666.09
    K2 = 1282.71

    # Cálculo de la radiancia
    radiance_band6 = (ML * band6) + AL

    # Cálculo de la temperatura de brillo
    bt = (K2 / np.log((K1 / radiance_band6) + 1)) - 273.15

    # Cálculo del NDVI
    ndvi = (band4 - band3) / (band4 + band3)

    # Cálculo de la emisividad
    emisivity = (0.004 * ndvi) + 0.986
    emisivity[emisivity <= 0] = 0.986

    # Cálculo de la temperatura superficial (LST)
    lst = bt / (1 + (0.00115 * bt / 1.4388) * np.log(emisivity))
    lst[lst < 0] = -9999

    # Crear un archivo TIFF para guardar el resultado
    driver = gdal.GetDriverByName('GTiff')
    out_ds = driver.Create(output_path, band3_ds.RasterXSize, band3_ds.RasterYSize, 1, gdal.GDT_Float32)
    out_ds.SetGeoTransform(band3_ds.GetGeoTransform())
    out_ds.SetProjection(band3_ds.GetProjection())
    
    # Escribir los datos calculados
    out_band = out_ds.GetRasterBand(1)
    out_band.WriteArray(lst)
    out_band.SetNoDataValue(-9999)
    out_band.FlushCache()
    
    # Cerrar datasets
    band3_ds = None
    band4_ds = None
    band6_ds = None
    out_ds = None

def apply_color_ramp(layer):
    """Aplica una rampa de colores continua desde amarillo a rojo oscuro y muestra los valores exactos."""
    if layer.isValid():
        # Obtener el rango de valores del raster
        provider = layer.dataProvider()
        stats = provider.bandStatistics(1)
        min_value = stats.minimumValue
        max_value = stats.maximumValue

        # Crear una rampa de color que empiece en amarillo y termine en rojo oscuro
        color_ramp_shader = QgsColorRampShader()
        color_ramp_shader.setColorRampType(QgsColorRampShader.Interpolated)

        # Definir la rampa de color
        color_ramp_shader.setColorRampItemList([
            QgsColorRampShader.ColorRampItem(min_value, QColor(255, 255, 0), f"{min_value:.2f}°C"),  # Amarillo
            QgsColorRampShader.ColorRampItem(min_value + (max_value - min_value) * 0.33, QColor(255, 165, 0), f"{(min_value + (max_value - min_value) * 0.33):.2f}°C"),  # Anaranjado
            QgsColorRampShader.ColorRampItem(min_value + (max_value - min_value) * 0.66, QColor(255, 69, 0), f"{(min_value + (max_value - min_value) * 0.66):.2f}°C"),  # Rojo
            QgsColorRampShader.ColorRampItem(max_value, QColor(153, 0, 0), f"{max_value:.2f}°C")  # Rojo oscuro
        ])

        # Aplicar la rampa de color
        raster_shader = QgsRasterShader()
        raster_shader.setRasterShaderFunction(color_ramp_shader)
        renderer = QgsSingleBandPseudoColorRenderer(layer.dataProvider(), 1, raster_shader)

        # Asignar el renderizador a la capa
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
            band_3_path = os.path.join(date_path, "B3.tif")
            band_4_path = os.path.join(date_path, "B4.tif")
            band_6_path = os.path.join(date_path, "B6.tif")

            # Calcular LST
            lst_path = os.path.join(date_path, f"LST_{date_folder}.tif")
            calculate_lst_gdal(band_3_path, band_4_path, band_6_path, lst_path)
            lst_layer = add_layer_to_project(lst_path, f"LST_{date_folder}")

            # Aplicar la rampa de colores
            if lst_layer:
                apply_color_ramp(lst_layer)

def main():
    """Función principal para procesar todos los datos Landsat."""
    for year_folder in os.listdir(base_directory):
        year_path = os.path.join(base_directory, year_folder)
        if os.path.isdir(year_path):
            process_landsat_data(year_path)

# Ejecutar el proceso
main()
