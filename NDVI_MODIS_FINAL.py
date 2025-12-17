import os
import numpy as np
from osgeo import gdal, ogr
from qgis.core import QgsRasterLayer, QgsProject, QgsColorRampShader, QgsRasterShader, QgsSingleBandPseudoColorRenderer
from PyQt5.QtGui import QColor

def reproyectar_raster(input_path, output_path, epsg):
    gdal.Warp(output_path, input_path, dstSRS=f"EPSG:{epsg}")
    return output_path

def agregar_raster_a_qgis(raster_path):
    layer = QgsRasterLayer(raster_path, os.path.basename(raster_path))
    if not layer.isValid():
        print(f"No se pudo cargar la capa: {raster_path}")
        return
    
    # Configuración de simbología con 4 categorías en tonos azules
    shader = QgsRasterShader()
    color_ramp = QgsColorRampShader()
    color_ramp.setColorRampItemList([
        QgsColorRampShader.ColorRampItem(-1.0, QColor(255, 255, 255, 0)),  # Transparente
        QgsColorRampShader.ColorRampItem(0.0, QColor(165, 42, 42)),        # Marrón (suelo seco)
        QgsColorRampShader.ColorRampItem(0.3, QColor(190, 255, 150)),      # Verde claro
        QgsColorRampShader.ColorRampItem(0.6, QColor(34, 139, 34)),        # Verde medio
        QgsColorRampShader.ColorRampItem(1.0, QColor(0, 100, 0))           # Verde oscuro
    ])
    color_ramp.setColorRampType(QgsColorRampShader.Interpolated)
    shader.setRasterShaderFunction(color_ramp)
    renderer = QgsSingleBandPseudoColorRenderer(layer.dataProvider(), 1, shader)
    layer.setRenderer(renderer)
    
    QgsProject.instance().addMapLayer(layer)
    print(f"Raster agregado a QGIS: {raster_path}")

def calcular_NDVI(hdf_path, mask_shp):
    output_folder = os.path.dirname(hdf_path)
    folder_name = os.path.basename(output_folder)
    
    hdf_dataset = gdal.Open(hdf_path, gdal.GA_ReadOnly)
    if not hdf_dataset:
        print(f"No se pudo abrir el archivo: {hdf_path}")
        return
    
    b01_subdataset = "MOD_Grid_500m_Surface_Reflectance:sur_refl_b01"
    b02_subdataset = "MOD_Grid_500m_Surface_Reflectance:sur_refl_b02"
    
    subdatasets = hdf_dataset.GetSubDatasets()
    b01_path = next((s[0] for s in subdatasets if b01_subdataset in s[0]), None)
    b02_path = next((s[0] for s in subdatasets if b02_subdataset in s[0]), None)
    
    if not b01_path or not b02_path:
        print("No se encontraron las bandas necesarias en el archivo HDF.")
        return
    
    b01_reproj = reproyectar_raster(b01_path, os.path.join(output_folder, "b01_reproj.tif"), 32721)
    b02_reproj = reproyectar_raster(b02_path, os.path.join(output_folder, "b02_reproj.tif"), 32721)
    
    b01 = gdal.Open(b01_reproj).ReadAsArray().astype(np.float32)
    b02 = gdal.Open(b02_reproj).ReadAsArray().astype(np.float32)
    
    b01[b01 <= 0] = np.nan
    b02[b02 <= 0] = np.nan
    
    NDVI = np.where((b02 + b01) == 0, np.nan, (b02 - b01) / (b02 + b01))
    
    output_path = os.path.join(output_folder, f"NDVI_{folder_name}.tif")
    driver = gdal.GetDriverByName("GTiff")
    out_raster = driver.Create(output_path, b01.shape[1], b01.shape[0], 1, gdal.GDT_Float32)
    out_raster.GetRasterBand(1).WriteArray(NDVI)
    out_raster.GetRasterBand(1).SetNoDataValue(np.nan)
    
    ref_ds = gdal.Open(b01_reproj)
    out_raster.SetProjection(ref_ds.GetProjection())
    out_raster.SetGeoTransform(ref_ds.GetGeoTransform())
    
    out_raster.FlushCache()
    print(f"NDVI guardado en: {output_path}")
    
    agregar_raster_a_qgis(output_path)
    
    if mask_shp:
        clipped_output_path = os.path.join(output_folder, f"NDVI_{folder_name}_BENJAMIN_ACEVAL.tif")
        gdal.Warp(clipped_output_path, output_path, cutlineDSName=mask_shp, cropToCutline=True, dstNodata=np.nan)
        print(f"NDVI recortado guardado en: {clipped_output_path}")
        agregar_raster_a_qgis(clipped_output_path)

def procesar_modis_NDVI(base_folder, mask_shp):
    for root, _, files in os.walk(base_folder):
        for file in files:
            if file.startswith("MOD09A1") and file.endswith(".hdf"):
                hdf_path = os.path.join(root, file)
                print(f"Procesando: {hdf_path}")
                calcular_NDVI(hdf_path, mask_shp)

base_directory = "E:/carmen_power/MODIS_AQUA"
mask_shapefile = "E:/CARMEN/BENJAMIN ACEVAL.shp"
procesar_modis_NDVI(base_directory, mask_shapefile)
