import sys
import socket
import getopt
import threading
import subprocess

# Global Variables
listen 				= False
command 			= False
upload 				= False
execute 			= ""
target 				= ""
upload_destination 	= ""
port 				= 0

def usage():
	print "_________ LoCat// Logan's Net Tool ________\n"
	print ">> locat.py -t [target_host] -p [port]"
	print "___________________________________________\n"
	print "Arguments//"
	print "  -l --listen 			// Listen on [host]:[port] for incoming connections"
	print "  -e --execute=[file_to_run] 	// Execute [file_to_run] upon receiving a connection"
	print "  -c --command 			// Initialize a sexy command shell"
	print "  -u --upload=[destination] 	// Upload a file to [destination] upon connection"
	print "\n"
	print "Examples//"
	print "  >> locat.py -t 192.168.0.1 -p 5555 -l -c"
	print "  >> locat.py -t 192.168.0.1 -p 5555 -l -u=C:\\target.exe"
	print "  >> locat.py -t 192.168.0.1 -p 5555 -l -e=\"cat /etc/passwd\""
	print "  >> echo 'ABVDEFGHI' | ./locat.py -t 192.168.0.12 -p 135"
	print ""
	sys.exit(0)

def main():
	global listen
	global port
	global execute
	global command
	global upload_destination
	global target

	if not len(sys.argv[1:]):
		usage()

	# Read Arguments
	try:
		opts, args = getopt.getopt(sys.argv[1:], "hle:t:p:cu", ["help", "listen", "execute", "target", "port", "command", "upload"])
	except getopt.GetoptError as err:
		print str(err)
		usage()


	for o, a in opts:
		if o in ("-h", "--help"):
			usage()
		elif o in ("-l", "--listen"):
			listen = True
		elif o in ("-e", "--execute"):
			execute = a
		elif o in ("-c", "--commandshell"):
			command = True
		elif o in ("-u", "--upload"):
			upload_destination = a
		elif o in ("-t", "--target"):
			target = a
		elif o in ("-p", "--port"):
			port = int(a)
		else:
			assert False, "Fucked up Option!"


	# Listen or Send Data from Stdin?
	if not listen and len(target) and port > 0:
		# Read in buffer from command line
		# Send Ctrl-D to bypass if not sending input to stdin
		buffer = sys.stdin.read()

		# Send Data
		client_sender(buffer)

	# Here is where we are going to listen, potentially upload things, execute commands, and drop a shell back depending on the command line options above.
	if listen:
		server_loop()

def client_sender(buffer):
	client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	try:
		# Connect
		client.connect((target, port))
		# Send
		if len(buffer):
			client.send(buffer)

		while True:
			# Wait fo' data
			recv_len = 1
			response = ""

			while recv_len:
				data = client.recv(4096)
				recv_len = len(data)
				response += data
				if recv_len < 4096:
					break

			print response,

			# Wait for more input
			buffer = raw_input("")
			buffer += "\n"

			# Send it off
			client.send(buffer)

	except:
		print "[*] Fat Exception.. Exiting."
		# Close the connection
		client.close()

def server_loop():
	global target

	# No target? Listen on all interfaces
	if not len(target):
		target = "0.0.0.0"

	# Bind and Listen on the given target, port
	server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	server.bind((target, port))
	server.listen(5)

	while True:
		client_socket, addr = server.accept()

		# Spin up thread to handle client
		client_thread = threading.Thread(target=client_handler, args=(client_socket,))
		client_thread.start()

def run_command(command):
	# Trim newline
	command = command.rstrip()

	# Run it
	try:
		output = subprocess.check_output(command, stderr=subprocess.STDOUT, shell=True)
	except:
		output = "Failed to execute command: %s\r\n" % command

	# Send output back to client
	return output

def client_handler(client_socket):
	global upload
	global execute
	global command

	# Check for Upload
	if len(upload_destination):
		# Read in all bytes
		file_buffer = ""
		while True:
			data = client_socket.recv(1024)
			if not data:
				break
			else:
				file_buffer += data

		# Write
		try:
			file_descriptor = open(upload_destination, "wb")
			file_descriptor.write(file_buffer)
			file_descriptor.close()

			client_socket.send("Successfully banged that file to %s\r\n" % upload_destination)
		except:
			client_socket.send("Failed to bang that file to %s\r\n" % upload_destination)

	# Check for Command Execution
	if len(execute):
		# Run Command
		output = run_command(execute)
		client_socket.send(output)

	# Check for Command Shell
	if command:
		while True:
			# Simple Prompt
			client_socket.send("<LoCat:#> ")

			# Let's receive until we detect line feed
			cmd_buffer = ""
			while "\n" not in cmd_buffer:
				cmd_buffer += client_socket.recv(1024)

			# Send back Command Output
			response = run_command(cmd_buffer)
			client_socket.send(response)

main()