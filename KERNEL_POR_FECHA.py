import os
import numpy as np
from osgeo import gdal, osr
from scipy.ndimage import gaussian_filter
from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsRasterLayer,
    QgsSingleBandPseudoColorRenderer,
    QgsRasterShader,
    QgsColorRampShader,
    QgsWkbTypes
)
from PyQt5.QtGui import QColor

# Directorio base donde están los años
base_directory = r'D:\KIM_USER\Tesis\KERNEL'

# Parámetros del kernel
radius = 4500  # Radio en metros
pixel_size = 300  # Tamaño del píxel en metros (X e Y)

# Recorrer cada año (carpetas en el directorio base)
for year in os.listdir(base_directory):
    year_path = os.path.join(base_directory, year)
    
    # Asegurarse de que la carpeta es un directorio (por si hay archivos sueltos)
    if os.path.isdir(year_path):
        # Recorrer cada subcarpeta de fecha (dentro de cada año)
        for date_folder in os.listdir(year_path):
            date_path = os.path.join(year_path, date_folder)
            
            # Asegurarse de que es un directorio válido
            if os.path.isdir(date_path):
                # Buscar cualquier archivo .shp en la carpeta
                shapefile_found = False
                for file in os.listdir(date_path):
                    if file.endswith('.shp'):
                        input_shapefile = os.path.join(date_path, file)
                        shapefile_found = True
                        break

                if not shapefile_found:
                    print(f"No se encontró un archivo .shp en {date_path}. Saltando...")
                    continue

                # Crear directorio de resultados si no existe
                output_directory = os.path.join(date_path, 'resultados')
                if not os.path.exists(output_directory):
                    os.makedirs(output_directory)
                    print(f"Directorio creado: {output_directory}")

                # Nombre de salida para el raster basado en la fecha de la carpeta
                output_raster = os.path.join(output_directory, f'KERNEL_{date_folder}.tif')
                print(f"Generando archivo raster: {output_raster}")

                # Cargar el shapefile como capa vectorial en QGIS
                layer = QgsVectorLayer(input_shapefile, "Puntos", "ogr")
                if not layer.isValid():
                    print(f"Error: La capa {input_shapefile} no es válida.")
                    continue
                else:
                    QgsProject.instance().addMapLayer(layer)

                    # Verificar si es una capa de puntos
                    if layer.geometryType() != QgsWkbTypes.PointGeometry:
                        print(f"El shapefile {input_shapefile} no es de puntos. Saltando...")
                        continue

                    # Extraer las coordenadas de los puntos
                    points = []
                    for feature in layer.getFeatures():
                        geom = feature.geometry()
                        if geom.isEmpty():
                            continue
                        points.append((geom.asPoint().x(), geom.asPoint().y()))

                    # Verificar los puntos extraídos
                    print(f"Puntos extraídos: {len(points)}")
                    if not points:
                        print(f"No se encontraron puntos en el shapefile {input_shapefile}. Saltando...")
                        continue

                    points = np.array(points)

                    # Definir el tamaño de la matriz en función del área de los puntos y la resolución
                    min_x, min_y, max_x, max_y = layer.extent().xMinimum(), layer.extent().yMinimum(), layer.extent().xMaximum(), layer.extent().yMaximum()

                    n_cols = int((max_x - min_x) / pixel_size) + 1  # +1 para incluir el borde
                    n_rows = int((max_y - min_y) / pixel_size) + 1  # +1 para incluir el borde

                    # Crear una matriz vacía para la densidad
                    density = np.zeros((n_rows, n_cols))

                    # Convertir las coordenadas de puntos a celdas de la cuadrícula
                    x_indices = ((points[:, 0] - min_x) / pixel_size).astype(int)
                    y_indices = ((max_y - points[:, 1]) / pixel_size).astype(int)

                    # Verificar los índices de las celdas
                    print(f"x_indices: {x_indices[:5]}... y_indices: {y_indices[:5]}...")  # Mostrar los primeros 5 índices

                    # Llenar la matriz con los conteos de puntos
                    for x, y in zip(x_indices, y_indices):
                        if 0 <= x < n_cols and 0 <= y < n_rows:  # Verificar que las coordenadas estén dentro del rango
                            density[y, x] += 1

                    # Aplicar un filtro gaussiano para simular el kernel
                    sigma = radius / pixel_size
                    density = gaussian_filter(density, sigma=sigma)

                    # Verificar la densidad generada
                    print(f"Densidad calculada, min: {np.min(density)}, max: {np.max(density)}")

                    # Guardar la matriz como un archivo raster usando GDAL
                    driver = gdal.GetDriverByName('GTiff')
                    out_raster = driver.Create(output_raster, n_cols, n_rows, 1, gdal.GDT_Float32)

                    # Definir la transformación geo-espacial (ubicación del raster en el espacio)
                    out_raster.SetGeoTransform((min_x, pixel_size, 0, max_y, 0, -pixel_size))

                    # Obtener referencia espacial con EPSG:32721 (UTM Zona 21S)
                    srs = osr.SpatialReference()
                    srs.ImportFromEPSG(32721)  # EPSG:32721 para UTM Zona 21S
                    out_raster.SetProjection(srs.ExportToWkt())

                    # Escribir la densidad en el raster
                    outband = out_raster.GetRasterBand(1)
                    outband.WriteArray(density)

                    # Establecer el valor no válido para que el raster se procese correctamente
                    outband.SetNoDataValue(-9999)
                    outband.FlushCache()

                    # Cerrar el archivo raster para asegurarse de que se escriben los datos
                    outband = None
                    out_raster = None

                    print(f"Densidad de kernel guardada en: {output_raster}")

                    # Agregar el raster a QGIS
                    raster_layer = QgsRasterLayer(output_raster, f"Densidad Kernel {date_folder}")

                    if raster_layer.isValid():
                        QgsProject.instance().addMapLayer(raster_layer)

                        # Crear un shader de rampa de colores
                        color_ramp_shader = QgsColorRampShader()
                        color_ramp_shader.setColorRampType(QgsColorRampShader.Interpolated)

                        # Obtener los valores mínimo y máximo del raster
                        min_value = np.min(density)
                        max_value = np.max(density)

                        # Definir la rampa de colores usando los tonos indicados
                        color_ramp_shader.setColorRampItemList([ 
                            QgsColorRampShader.ColorRampItem(min_value, QColor(255, 247, 181), 'Bajas Densidades'),
                            QgsColorRampShader.ColorRampItem(min_value + (max_value - min_value) * 0.1, QColor(255, 169, 49), 'Densidades Medias'),
                            QgsColorRampShader.ColorRampItem(min_value + (max_value - min_value) * 0.5, QColor(255, 51, 51), 'Densidades Altas'),
                            QgsColorRampShader.ColorRampItem(max_value, QColor(153, 0, 0), 'Máxima Densidad'),
                        ])

                        # Crear el shader raster y asignar el color ramp shader
                        raster_shader = QgsRasterShader()
                        raster_shader.setRasterShaderFunction(color_ramp_shader)

                        # Crear el renderer
                        renderer = QgsSingleBandPseudoColorRenderer(raster_layer.dataProvider(), 1, raster_shader)

                        # Asignar el renderer a la capa
                        raster_layer.setRenderer(renderer)

                        # Ajustar la opacidad del renderizador
                        renderer.setOpacity(0.76)

                        print(f"Opacidad ajustada al 76% para el kernel de la fecha {date_folder}.")
                    else:
                        print(f"Error: la capa raster no es válida para {date_folder}.")
                
print("Proceso completado.")
