import subprocess
import os

carpeta_actual = os.path.dirname(os.path.abspath(__file__))
ruta_app = os.path.join(carpeta_actual, "app.py")

# Ejecutamos Streamlit normal para que abra Chrome automáticamente
subprocess.run(["streamlit", "run", ruta_app])