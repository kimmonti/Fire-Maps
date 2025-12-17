import os
from osgeo import gdal
import numpy as np
from qgis.core import QgsProject, QgsRasterLayer

# Parámetros de entrada
base_directory = r"C:\Users\rodov\Downloads\LANDSAT 8 OLI"

def add_layer_to_project(path, name):
    """Añade una capa raster al proyecto QGIS."""
    layer = QgsRasterLayer(path, name)
    if layer.isValid():
        QgsProject.instance().addMapLayer(layer)
        return layer
    else:
        print(f"Error al cargar la capa {name}")
        return None

def scale_to_byte(arr):
    """Escala un array numpy a valores de 0-255."""
    arr_min = np.min(arr)
    arr_max = np.max(arr)
    scale = 255 / (arr_max - arr_min) if arr_max > arr_min else 1
    scaled_arr = ((arr - arr_min) * scale).astype(np.uint8)
    return scaled_arr

def combine_bands(band2_path, band5_path, band6_path, output_path):
    """Combina las bandas 6, 5 y 2 en un solo archivo TIFF (RGB)."""
    # Abrir las bandas usando GDAL
    band2_ds = gdal.Open(band2_path)
    band5_ds = gdal.Open(band5_path)
    band6_ds = gdal.Open(band6_path)
    
    # Leer los datos de las bandas
    band2 = band2_ds.GetRasterBand(1).ReadAsArray()
    band5 = band5_ds.GetRasterBand(1).ReadAsArray()
    band6 = band6_ds.GetRasterBand(1).ReadAsArray()

    # Escalar las bandas a 0-255
    band2_scaled = scale_to_byte(band2)
    band5_scaled = scale_to_byte(band5)
    band6_scaled = scale_to_byte(band6)

    # Crear un archivo TIFF para guardar el resultado RGB
    combined = gdal.GetDriverByName('GTiff').Create(output_path, 
                  band2_ds.RasterXSize, band2_ds.RasterYSize, 
                  3, gdal.GDT_Byte)

    # Escribir las bandas en el archivo de salida en el orden RGB especificado
    combined.GetRasterBand(1).WriteArray(band6_scaled)  # Banda 6 - Red
    combined.GetRasterBand(2).WriteArray(band5_scaled)  # Banda 5 - Green
    combined.GetRasterBand(3).WriteArray(band2_scaled)  # Banda 2 - Blue

    # Configurar la proyección y la transformación geográfica
    combined.SetGeoTransform(band2_ds.GetGeoTransform())
    combined.SetProjection(band2_ds.GetProjection())
    combined.FlushCache()

    # Cerrar datasets
    band2_ds = None
    band5_ds = None
    band6_ds = None
    combined = None

def process_landsat_data(year_folder):
    """Procesa los datos Landsat para cada carpeta de fecha."""
    for date_folder in os.listdir(year_folder):
        date_path = os.path.join(year_folder, date_folder)
        if os.path.isdir(date_path):
            # Definir las rutas de las bandas
            band_2_path = os.path.join(date_path, "B2.tif")
            band_5_path = os.path.join(date_path, "B5.tif")
            band_6_path = os.path.join(date_path, "B6.tif")

            # Verificar que todas las bandas existan
            if os.path.exists(band_2_path) and os.path.exists(band_5_path) and os.path.exists(band_6_path):
                # Ruta de salida para la banda combinada
                combined_path = os.path.join(date_path, f"Combined_B6_B5_B2_{date_folder}.tif")
                combine_bands(band_2_path, band_5_path, band_6_path, combined_path)
                combined_layer = add_layer_to_project(combined_path, f"Combined_B6_B5_B2_{date_folder}")

def main():
    """Función principal para procesar todos los datos Landsat."""
    for year_folder in os.listdir(base_directory):
        year_path = os.path.join(base_directory, year_folder)
        if os.path.isdir(year_path):
            process_landsat_data(year_path)

# Ejecutar el proceso
main()
