from google.cloud import storage
import cv2
import numpy as np
import io
import pandas as pd
import os
from PIL import Image
from threading import Lock
from io import BytesIO
import time

class StorageClient:
    _instance = None
    _lock = Lock()
    
    def __init__(self, windir=None, bucket_name=None):
        # Consider empty string bucket_name as None
        self.is_gcp = bucket_name is not None and bucket_name != ""
        self.windir = windir if windir else ""
        print(f"Storage mode: {'GCP' if self.is_gcp else 'Windows'}")
        if self.is_gcp:
            self._client = storage.Client()
            self._bucket = self._client.bucket(bucket_name)
            
    @classmethod
    def get_instance(cls, windir=None, bucket_name=None):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(windir, bucket_name)
        return cls._instance

def read_image(path, use_pil=False, max_retries=3):
    storage = StorageClient.get_instance()
    
    try:
        if storage.is_gcp:
            blob = storage._bucket.blob(path.replace('//', '/').rstrip('/'))
            
            for attempt in range(max_retries):
                try:
                    bytes_data = blob.download_as_bytes()
                    break
                except Exception as e:
                    if attempt == max_retries - 1:
                        print(f"Failed to download from GCP after {max_retries} attempts: {str(e)}")
                        return None
                    print(f"Download attempt {attempt + 1} failed, retrying...")
                    time.sleep(1 * (attempt + 1))
            
            if use_pil:
                return Image.open(BytesIO(bytes_data))
            else:
                nparr = np.frombuffer(bytes_data, np.uint8)
                return cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        else:
            full_path = os.path.join(storage.windir, path)
            if use_pil:
                return Image.open(full_path)
            else:
                return cv2.imread(full_path)
                
    except Exception as e:
        print(f"Error reading image {path}: {str(e)}")
        return None

def read_csv(path):
    storage = StorageClient.get_instance()
    
    if storage.is_gcp:
        blob = storage._bucket.blob(path.replace('//', '/').rstrip('/'))
        content = blob.download_as_string()
        return pd.read_csv(io.BytesIO(content))
    else:
        full_path = os.path.join(storage.windir, path)
        return pd.read_csv(full_path)

def save_data(data, path):
    storage = StorageClient.get_instance()
    
    # Convert PIL Image to numpy array if needed
    if isinstance(data, Image.Image):
        data = np.array(data)
        # Convert RGB to BGR for OpenCV
        if len(data.shape) == 3 and data.shape[2] == 3:  # Check if it's a color image
            data = cv2.cvtColor(data, cv2.COLOR_RGB2BGR)
        
    if storage.is_gcp:
        blob = storage._bucket.blob(path.replace('//', '/').rstrip('/'))
        
        if isinstance(data, np.ndarray):
            _, encoded = cv2.imencode('.png', data)
            blob.upload_from_string(encoded.tobytes())
        elif isinstance(data, (pd.DataFrame, pd.Series)):
            buffer = io.StringIO()
            data.to_csv(buffer, index=False)
            blob.upload_from_string(buffer.getvalue())
        else:
            blob.upload_from_string(str(data))
    else:
        full_path = os.path.join(storage.windir, path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        if isinstance(data, np.ndarray):
            cv2.imwrite(full_path, data)
        elif isinstance(data, (pd.DataFrame, pd.Series)):
            data.to_csv(full_path, index=False)
        else:
            with open(full_path, 'w') as f:
                f.write(str(data))

def file_exists(path):
    storage = StorageClient.get_instance()
    
    if storage.is_gcp:
        blob = storage._bucket.blob(path.replace('//', '/').rstrip('/'))
        return blob.exists()
    else:
        full_path = os.path.join(storage.windir, path)
        return os.path.exists(full_path)
    
    
    
def make_dirs(path):
    storage = StorageClient.get_instance()
    
    # Only create directories for local storage
    if not storage.is_gcp:
        full_path = os.path.join(storage.windir, path)
        os.makedirs(full_path, exist_ok=True)
