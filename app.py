from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import pandas as pd
import wfdb
import numpy as np
from io import BytesIO
import zipfile

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = r"C:\Users\parkm\Desktop"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/upload', methods=['POST'])
def upload_csv():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "파일을 찾을 수 없습니다."}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "파일 이름이 비어 있습니다."}), 400
        if not file.filename.endswith('.csv'):
            return jsonify({"error": "CSV 파일만 업로드 가능합니다."}), 400

        csv_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(csv_path)

        df = pd.read_csv(csv_path)
        # 첫 번째 열 사용, 없으면 에러
        if df.empty or df.columns.size == 0:
            return jsonify({"error": "CSV 파일이 비어 있거나 열이 없습니다."}), 400
        signal = df.iloc[:, 0].values  # 첫 번째 열
        # float64로 강제 변환
        signal = np.array(signal, dtype=np.float64)

        base_name = os.path.splitext(file.filename)[0]
        dat_path = os.path.join(UPLOAD_FOLDER, f"{base_name}.dat")
        hea_path = os.path.join(UPLOAD_FOLDER, f"{base_name}.hea")

        # WFDB 파일 생성
        wfdb.wrsamp(base_name, fs=100, units=['mV'], sig_name=['signal'], 
                    p_signal=signal.reshape(-1, 1), fmt=['16'], adc_gain=[200], 
                    baseline=[0], comments=['Generated from CSV'], write_dir=UPLOAD_FOLDER)

        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.write(dat_path, f"{base_name}.dat")
            zip_file.write(hea_path, f"{base_name}.hea")
        zip_buffer.seek(0)

        return send_file(
            zip_buffer,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f"{base_name}_wfdb.zip"
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
