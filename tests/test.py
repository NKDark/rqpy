import os
import socket
import time

from rqpy import Device, Engine, Packet


def send_data(conn: socket.socket, data: bytes):
    conn.sendall((len(data) + 4).to_bytes(4, byteorder='big'))
    conn.sendall(data)
    pass


def read_data(conn: socket.socket) -> bytes:
    length = int.from_bytes(conn.recv(4), 'big')
    return conn.recv(length - 4)


def send_and_wait(conn: socket.socket, engine: Engine, pkt: Packet) -> Packet:
    send_data(conn, engine.encode_packet(pkt))
    data = read_data(conn)
    return engine.decode_packet(data)


def main():
    device_file = "device.json"
    device = Device.random()
    if os.path.exists(device_file):
        with open(device_file, "r") as f:
            device = Device.from_str(f.read())
    else:
        with open(device_file, "w") as f:
            f.write(device.to_str())

    engine = Engine(device, 1)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect(('42.81.176.211', 443))
        req = engine.build_qrcode_fetch_request_packet()
        resp = send_and_wait(s, engine, req)
        qrcode = engine.decode_trans_emp_response(resp.body).image_fetch

        with open("qrcode.png", "wb") as f:
            f.write(qrcode.image)
        print("qrcode.png")

        sig = qrcode.sig
        while True:
            req = engine.build_qrcode_result_query_request_packet(sig)
            resp = send_and_wait(s, engine, req)
            state = engine.decode_trans_emp_response(resp.body)
            if state.waiting_for_scan:
                print("waiting_for_scan")
            if state.waiting_for_confirm:
                print("waiting_for_confirm")
            if state.timeout:
                print("timeout")
            if state.canceled:
                print("canceled")
            if state.confirmed:
                print("confirmed")
                print("uin {}".format(state.confirmed.uin))
                req = engine.build_qrcode_login_packet(
                    state.confirmed.tmp_pwd,
                    state.confirmed.tmp_no_pic_sig,
                    state.confirmed.tgt_qr
                )
                resp = send_and_wait(s, engine, req)
                login_response = engine.decode_login_response(resp.body)
                if login_response.device_lock_login:
                    req = engine.build_device_lock_login_packet()
                    resp = send_and_wait(s, engine, req)
                    login_response = engine.decode_login_response(resp.body)

                print(login_response.success.account_info.nick)
                print(login_response.success.account_info.age)
                print(login_response.success.account_info.gender)
                print("login success")
                break
            time.sleep(1)

        req = engine.build_client_register_packet()
        resp = send_and_wait(s, engine, req)
        print(resp)


if __name__ == '__main__':
    main()
