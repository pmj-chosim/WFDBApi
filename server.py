from flask import Flask, request, jsonify, send_file
from flask_cors import CORS  # CORS 활성화
import os
import csv
import numpy as np
import struct
import io  # 바이너리 데이터를 메모리에서 처리하기 위해 사용

app = Flask(__name__)
CORS(app)  # 다른 도메인에서도 접근 가능하게 설정

def read_csv(file):
    """CSV 파일을 읽어 numpy 배열로 변환"""
    data = []
    file.stream.seek(0)  # 파일 스트림을 처음 위치로 되돌리기
    text_file = file.stream.read().decode("utf-8").splitlines()  # UTF-8 텍스트로 변환

    reader = csv.reader(text_file)
    headers = next(reader)  

    for row in reader:
        data.append([int(val) for val in row])  

    data = np.array(data)
    return headers, data


def csv_to_wfdb(file, record_name, sampling_rate=250):
    """CSV 데이터를 WFDB 형식으로 변환 (서버에 저장하지 않고 반환)"""
    
    headers, data = read_csv(file)
    num_samples, num_channels = data.shape

    max_value = data.max()
    min_value = data.min()
    print(f"데이터 범위: {min_value} ~ {max_value}")

    use_64bit = (max_value > 2_147_483_647 or min_value < -2_147_483_648)
    use_32bit = (max_value > 32767 or min_value < -32768)

    # 데이터 파일을 메모리에서 처리
    dat_buffer = io.BytesIO()
    hea_buffer = io.StringIO()

    # .dat 파일 생성
    for sample in data:
        for value in sample:
            if use_64bit:
                dat_buffer.write(struct.pack("<q", value))  # 64비트 저장
            elif use_32bit:
                dat_buffer.write(struct.pack("<i", value))  # 32비트 저장
            else:
                dat_buffer.write(struct.pack("<h", value))  # 16비트 저장

    # .hea 파일 생성
    format_code = 64 if use_64bit else (32 if use_32bit else 16)
    hea_buffer.write(f"{record_name} {num_channels} {sampling_rate} {num_samples}\n")

    for i, channel_name in enumerate(headers):
        hea_buffer.write(f"{record_name}.dat {format_code} 1000 0 mV 0 0 {channel_name}\n")

    # 메모리에서 파일을 클라이언트에 반환
    dat_buffer.seek(0)
    hea_buffer.seek(0)
    
    return dat_buffer, hea_buffer

@app.route('/upload', methods=['POST'])
def upload_and_convert_csv():
    """CSV 파일을 업로드하고 WFDB로 변환 후 클라이언트에 반환"""
    if 'file' not in request.files:
        return jsonify({"error": "파일을 찾을 수 없습니다."}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "파일 이름이 비어 있습니다."}), 400

    if not file.filename.endswith('.csv'):
        return jsonify({"error": "CSV 파일만 업로드 가능합니다."}), 400

    # 변환 실행
    record_name = os.path.splitext(file.filename)[0] + "_wfdb"
    dat_buffer, hea_buffer = csv_to_wfdb(file, record_name)

    return jsonify({
        "message": f"파일 '{file.filename}'이 변환 완료!",
        "dat_content": dat_buffer.getvalue().hex(),  # 바이너리 데이터를 16진수로 변환
        "hea_content": hea_buffer.getvalue()
    }), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)  # 외부 접속 가능
