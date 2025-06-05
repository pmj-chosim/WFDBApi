from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import pandas as pd
import wfdb
import numpy as np
from io import BytesIO
import zipfile
import logging
import os
import tempfile
import shutil

app = Flask(__name__)
CORS(app)

# 로그 설정
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@app.route('/upload', methods=['POST'])
def upload_csv():
    try:
        logger.info("파일 업로드 요청 수신")
        if 'file' not in request.files:
            logger.error("파일이 요청에 포함되지 않음")
            return jsonify({"error": "파일을 찾을 수 없습니다."}), 400

        file = request.files['file']
        if file.filename == '':
            logger.error("파일 이름이 비어 있음")
            return jsonify({"error": "파일 이름이 비어 있습니다."}), 400
        if not file.filename.endswith('.csv'):
            logger.error("업로드된 파일이 CSV 형식이 아님")
            return jsonify({"error": "CSV 파일만 업로드 가능합니다."}), 400

        # 임시 디렉토리 생성
        temp_dir = tempfile.mkdtemp()
        logger.info(f"임시 디렉토리 생성: {temp_dir}")

        # CSV 파일을 임시 디렉토리에 저장
        base_name = os.path.splitext(file.filename)[0]
        csv_path = os.path.join(temp_dir, file.filename)
        file.save(csv_path)
        logger.info(f"CSV 파일 저장: {csv_path}")

        # CSV 읽기
        df = pd.read_csv(csv_path)
        if df.empty or df.columns.size == 0:
            logger.error("CSV 파일이 비어 있거나 열이 없음")
            shutil.rmtree(temp_dir)  # 임시 디렉토리 삭제
            return jsonify({"error": "CSV 파일이 비어 있거나 열이 없습니다."}), 400
        signal = df.iloc[:, 0].values
        signal = np.array(signal, dtype=np.float64)
        logger.info(f"신호 데이터 크기: {len(signal)}")

        # WFDB 파일 생성
        dat_path = os.path.join(temp_dir, f"{base_name}.dat")
        hea_path = os.path.join(temp_dir, f"{base_name}.hea")
        logger.info(f"WFDB 파일 생성 경로: {dat_path}, {hea_path}")

        wfdb.wrsamp(
            record_name=base_name,
            fs=100,
            units=['mV'],
            sig_name=['signal'],
            p_signal=signal.reshape(-1, 1),
            fmt=['16'],
            adc_gain=[200],
            baseline=[0],
            comments=['Generated from CSV'],
            write_dir=temp_dir
        )

        # ZIP 파일 생성
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.write(dat_path, f"{base_name}.dat")
            zip_file.write(hea_path, f"{base_name}.hea")
        zip_buffer.seek(0)
        logger.info(f"ZIP 파일 생성 완료: {base_name}_wfdb.zip")

        # 임시 디렉토리 삭제
        shutil.rmtree(temp_dir)
        logger.info(f"임시 디렉토리 삭제: {temp_dir}")

        return send_file(
            zip_buffer,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f"{base_name}_wfdb.zip"
        )

    except Exception as e:
        logger.error(f"오류 발생: {str(e)}")
        if 'temp_dir' in locals():
            shutil.rmtree(temp_dir, ignore_errors=True)  # 에러 발생 시에도 임시 디렉토리 삭제
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
