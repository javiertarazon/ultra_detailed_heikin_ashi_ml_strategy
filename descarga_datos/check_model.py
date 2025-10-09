import joblib
import json
import os

# Verificar el modelo más reciente
model_files = [f for f in os.listdir('models/SOL_USDT') if f.endswith('.joblib')]
model_files.sort(reverse=True)
latest_model = model_files[0] if model_files else None

if latest_model:
    model_path = f'models/SOL_USDT/{latest_model}'
    print(f'Cargando modelo: {model_path}')
    model = joblib.load(model_path)
    print(f'Modelo cargado: {type(model)}')
    if hasattr(model, 'n_features_in_'):
        print(f'Features esperadas por el modelo: {model.n_features_in_}')
    
    # Verificar metadata
    metadata_file = latest_model.replace('.joblib', '_metadata.json')
    metadata_path = f'models/SOL_USDT/{metadata_file}'
    if os.path.exists(metadata_path):
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        print(f'Metadata completo: {json.dumps(metadata, indent=2)}')
        if 'features' in metadata:
            features_list = metadata['features']
            print(f'Features en metadata: {features_list}')
            print(f'Número de features en metadata: {len(features_list)}')
else:
    print('No se encontraron modelos')