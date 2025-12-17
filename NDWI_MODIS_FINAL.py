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
        QgsColorRampShader.ColorRampItem(-1, QColor(255, 255, 255, 0)),  # Transparente para NoData
        QgsColorRampShader.ColorRampItem(0.0, QColor(198, 219, 239)),    # Azul claro
        QgsColorRampShader.ColorRampItem(0.3, QColor(107, 174, 214)),   # Azul medio
        QgsColorRampShader.ColorRampItem(0.6, QColor(33, 113, 181)),    # Azul intenso
        QgsColorRampShader.ColorRampItem(1.0, QColor(8, 69, 148))       # Azul oscuro
    ])
    color_ramp.setColorRampType(QgsColorRampShader.Interpolated)
    shader.setRasterShaderFunction(color_ramp)
    renderer = QgsSingleBandPseudoColorRenderer(layer.dataProvider(), 1, shader)
    layer.setRenderer(renderer)
    
    QgsProject.instance().addMapLayer(layer)
    print(f"Raster agregado a QGIS: {raster_path}")

def calcular_ndwi(hdf_path, mask_shp):
    output_folder = os.path.dirname(hdf_path)
    folder_name = os.path.basename(output_folder)
    
    hdf_dataset = gdal.Open(hdf_path, gdal.GA_ReadOnly)
    if not hdf_dataset:
        print(f"No se pudo abrir el archivo: {hdf_path}")
        return
    
    b02_subdataset = "MOD_Grid_500m_Surface_Reflectance:sur_refl_b02"
    b05_subdataset = "MOD_Grid_500m_Surface_Reflectance:sur_refl_b05"
    
    subdatasets = hdf_dataset.GetSubDatasets()
    b02_path = next((s[0] for s in subdatasets if b02_subdataset in s[0]), None)
    b05_path = next((s[0] for s in subdatasets if b05_subdataset in s[0]), None)
    
    if not b02_path or not b05_path:
        print("No se encontraron las bandas necesarias en el archivo HDF.")
        return
    
    b02_reproj = reproyectar_raster(b02_path, os.path.join(output_folder, "b02_reproj.tif"), 32721)
    b05_reproj = reproyectar_raster(b05_path, os.path.join(output_folder, "b05_reproj.tif"), 32721)
    
    b02 = gdal.Open(b02_reproj).ReadAsArray().astype(np.float32)
    b05 = gdal.Open(b05_reproj).ReadAsArray().astype(np.float32)
    
    b02[b02 <= 0] = np.nan
    b05[b05 <= 0] = np.nan
    
    ndwi = np.where((b02 + b05) == 0, np.nan, (b02 - b05) / (b02 + b05))
    
    output_path = os.path.join(output_folder, f"NDWI_{folder_name}.tif")
    driver = gdal.GetDriverByName("GTiff")
    out_raster = driver.Create(output_path, b02.shape[1], b02.shape[0], 1, gdal.GDT_Float32)
    out_raster.GetRasterBand(1).WriteArray(ndwi)
    out_raster.GetRasterBand(1).SetNoDataValue(np.nan)
    
    ref_ds = gdal.Open(b02_reproj)
    out_raster.SetProjection(ref_ds.GetProjection())
    out_raster.SetGeoTransform(ref_ds.GetGeoTransform())
    
    out_raster.FlushCache()
    print(f"NDWI guardado en: {output_path}")
    
    agregar_raster_a_qgis(output_path)
    
    if mask_shp:
        clipped_output_path = os.path.join(output_folder, f"NDWI_{folder_name}_BENJAMIN_ACEVAL.tif")
        gdal.Warp(clipped_output_path, output_path, cutlineDSName=mask_shp, cropToCutline=True, dstNodata=np.nan)
        print(f"NDWI recortado guardado en: {clipped_output_path}")
        agregar_raster_a_qgis(clipped_output_path)

def procesar_modis_ndwi(base_folder, mask_shp):
    for root, _, files in os.walk(base_folder):
        for file in files:
            if file.startswith("MOD09A1") and file.endswith(".hdf"):
                hdf_path = os.path.join(root, file)
                print(f"Procesando: {hdf_path}")
                calcular_ndwi(hdf_path, mask_shp)

base_directory = "E:/carmen_power/MODIS_AQUA"
mask_shapefile = "E:/CARMEN/BENJAMIN ACEVAL.shp"
procesar_modis_ndwi(base_directory, mask_shapefile)
