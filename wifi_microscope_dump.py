# Proof-of-concept code for reading data from a Wifi microscope.
# See https://www.chzsoft.de/site/hardware/reverse-engineering-a-wifi-microscope/.

# Copyright (c) 2020, Christian Zietz <czietz@gmx.net>
# Copyright (c) 2023, mhrtmnn
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
# list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import socket
import numpy as np
import cv2
import signal
import sys

HOST = "192.168.29.1"	# Microscope hard-wired IP address
SPORT = 20000			# Microscope command port
RPORT = 10900			# Receive port for JPEG frames

def heartbeat(s):
	s.sendto(b"JHCMD\xd0\x01", (HOST, SPORT))

def display_frame(buf):
	arr = np.frombuffer(buf, dtype="uint8")
	img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
	# print(f"Decoded image: {img.shape}")
	cv2.namedWindow("wifi microscope", cv2.WINDOW_NORMAL)
	cv2.imshow("wifi microscope", img)
	cv2.waitKey(5)

def main():
	# Open command socket for sending
	with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sTx:
		# sTx.sendto(b"JHCMD\xd0\x00", (HOST, SPORT))
		# Send commands like naInit_Re() would do
		sTx.sendto(b"JHCMD\x10\x00", (HOST, SPORT))
		sTx.sendto(b"JHCMD\x20\x00", (HOST, SPORT))

		# Heartbeat command, starts the transmission of data from the scope
		heartbeat(sTx)
		heartbeat(sTx)

		imgBuf = bytearray()
		skipFirst = True

		# Open receive socket and bind to receive port
		with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sRx:
			sRx.bind(("", RPORT))
			sRx.settimeout(5.0)

			# clean exit
			def signal_handler(sig, frame):
				print('Closing stream ...')
				# Stop data command, like in naStop()
				sTx.sendto(b"JHCMD\xd0\x02", (HOST, SPORT))
				sRx.close()
				sTx.close()
				sys.exit(0)
			signal.signal(signal.SIGINT, signal_handler)

			print("Starting stream")
			while True:
				data = sRx.recv(1450)
				if len(data) > 8:
					# Header
					frameCount = data[0] + data[1]*256
					packetCount = data[3]

					# Data
					if packetCount==0:
						# A new frame has started
						# print(f"Frame {frameCount}")
						if not skipFirst:
							display_frame(imgBuf)
						skipFirst = False
						imgBuf = bytearray()

						# Send a heartbeat every 50 frames (arbitrary number) to keep data flowing
						if frameCount % 50 == 0:
							heartbeat(sTx)

					imgBuf += data[8:]

if __name__ == "__main__":
	main()
