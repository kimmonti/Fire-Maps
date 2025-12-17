import os
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

def calculate_ndwi(band3_path, band5_path, output_path):
    """Calcula el NDWI utilizando GDAL y guarda el resultado."""
    band3_ds = gdal.Open(band3_path)
    band5_ds = gdal.Open(band5_path)
    
    band3 = band3_ds.GetRasterBand(1).ReadAsArray().astype(float)
    band5 = band5_ds.GetRasterBand(1).ReadAsArray().astype(float)

    ndwi = (band3 - band5) / (band3 + band5)
    ndwi[np.isnan(ndwi)] = 0

    driver = gdal.GetDriverByName('GTiff')
    out_ds = driver.Create(output_path, band3_ds.RasterXSize, band3_ds.RasterYSize, 1, gdal.GDT_Float32)
    out_ds.SetGeoTransform(band3_ds.GetGeoTransform())
    out_ds.SetProjection(band3_ds.GetProjection())
    
    out_band = out_ds.GetRasterBand(1)
    out_band.WriteArray(ndwi)
    out_band.SetNoDataValue(-9999)
    out_band.FlushCache()
    
    band3_ds = None
    band5_ds = None
    out_ds = None

def apply_simple_color_ramp(layer):
    """Aplica una rampa de colores azul simple al raster NDWI con 4 clases."""
    if layer.isValid():
        provider = layer.dataProvider()

        # Crear una lista de colores para las clases (tonos de azul)
        color_mapping = [
            QgsColorRampShader.ColorRampItem(-1, QColor(0, 0, 255), "-1"),    # Azul oscuro
            QgsColorRampShader.ColorRampItem(0, QColor(0, 128, 255), "0"),    # Azul medio
            QgsColorRampShader.ColorRampItem(0.5, QColor(0, 191, 255), "0.5"), # Azul claro
            QgsColorRampShader.ColorRampItem(1, QColor(173, 216, 230), "1")   # Azul muy claro
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
            band_3_path = os.path.join(date_path, "B3.tif")
            band_5_path = os.path.join(date_path, "B5.tif")

            # Verificar si las bandas existen
            if not (os.path.exists(band_3_path) and os.path.exists(band_5_path)):
                print(f"Faltan algunas bandas en {date_path}.")
                continue

            # Calcular NDWI
            ndwi_path = os.path.join(date_path, f"NDWI_{date_folder}.tif")
            calculate_ndwi(band_3_path, band_5_path, ndwi_path)
            ndwi_layer = add_layer_to_project(ndwi_path, f"NDWI_{date_folder}")

            # Aplicar la rampa de colores
            if ndwi_layer:
                apply_simple_color_ramp(ndwi_layer)

def main():
    """Función principal para procesar todos los datos Landsat."""
    for year_folder in os.listdir(base_directory):
        year_path = os.path.join(base_directory, year_folder)
        if os.path.isdir(year_path):
            process_landsat_data(year_path)

# Ejecutar el proceso
main()
