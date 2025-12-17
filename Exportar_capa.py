import os
from qgis.core import QgsVectorFileWriter, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsProject

# Paso 1: Obtener la capa seleccionada en el panel de capas
layer = iface.layerTreeView().currentLayer()

# Comprobar si la capa es válida
if not layer:
    print("No hay ninguna capa seleccionada en el panel de capas.")
else:
    # Paso 2: Obtener la ruta completa del archivo original
    original_path = layer.source()
    
    # Verificar si la capa tiene una ruta válida (si es un archivo guardado)
    if original_path == '':
        print("La capa seleccionada no tiene una fuente válida o no es un archivo guardado.")
    else:
        # Obtener el directorio del archivo original
        original_dir = os.path.dirname(original_path)
        print(f"Directorio original: {original_dir}")

        # Definir el nombre del archivo exportado (con un sufijo para diferenciarlo)
        output_file_name = os.path.splitext(os.path.basename(original_path))[0] + "_EPSG32721.shp"
        
        # Crear la ruta de salida en el mismo directorio
        output_path = os.path.join(original_dir, output_file_name)

        # Definir el sistema de referencia de coordenadas de salida (EPSG:32721)
        crs = QgsCoordinateReferenceSystem('EPSG:32721')

        # Crear las opciones de exportación
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = "ESRI Shapefile"  # Formato de salida
        options.fileEncoding = "UTF-8"  # Codificación de archivo
        options.ct = QgsCoordinateTransform(layer.crs(), crs, QgsProject.instance())  # Convertir al SRC EPSG:32721

        # Exportar la capa completa (sin seleccionar entidades)
        error = QgsVectorFileWriter.writeAsVectorFormat(layer, output_path, options)

        if error[0] == QgsVectorFileWriter.NoError:
            print(f"Exportación completada correctamente en: {output_path}")

            # Paso 4: Eliminar la capa original (en EPSG:4326) del panel de capas
            layer_id = layer.id()  # Almacenar el ID de la capa para eliminarla después
            QgsProject.instance().removeMapLayer(layer_id)
            print(f"Capa original '{layer.name()}' eliminada del panel de capas.")
            
            # Paso 5: Eliminar el archivo original (EPSG:4326) del directorio
            # Se eliminan todos los archivos asociados (.shp, .shx, .dbf, etc.)
            base_name = os.path.splitext(original_path)[0]
            print(f"Base de nombre original: {base_name}")
            extensions = [".shp", ".shx", ".dbf", ".prj", ".cpg"]
            for ext in extensions:
                file_to_delete = base_name + ext
                print(f"Comprobando si el archivo existe: {file_to_delete}")
                if os.path.exists(file_to_delete):
                    try:
                        os.remove(file_to_delete)
                        print(f"Archivo eliminado: {file_to_delete}")
                    except Exception as e:
                        print(f"No se pudo eliminar el archivo {file_to_delete}: {e}")
                else:
                    print(f"El archivo no existe: {file_to_delete}")

            print("El archivo original ha sido eliminado del disco, mientras que el archivo exportado se ha mantenido.")
        else:
            print(f"Error al exportar: {error}")