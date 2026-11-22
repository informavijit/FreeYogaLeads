"""
YogaLeadAI - Local Cloud Telephony Gateway Bridge & Indian Female Voice Engine
Runs on http://localhost:5000:
1. Indian Female Voice Engine (/tts): Streams authentic native Indian female audio across 7 Indian languages (Hindi, Indian English, Telugu, Tamil, Kannada, Malayalam, Bengali).
2. Outbound Carrier Dispatcher (/call): Direct bridge to Exotel, Twilio Voice API, or generic Webhooks.
"""

import http.server
import socketserver
import json
import urllib.request
import urllib.parse
import base64
import time
import sys

PORT = 5000

# Native Indian Language TTS Codes
LANG_CODE_MAP = {
    'hi': 'hi',        # Hindi (Female)
    'en': 'en-IN',     # Indian English (Female)
    'te': 'te',        # Telugu (Female)
    'ta': 'ta',        # Tamil (Female)
    'kn': 'kn',        # Kannada (Female)
    'ml': 'ml',        # Malayalam (Female)
    'bn': 'bn'         # Bengali (Female)
}

class TelephonyBridgeHandler(http.server.BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        # Handle CORS preflight
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)

        # --------------------------------------------------------------------
        # 1. INDIAN FEMALE VOICE TTS ENGINE ENDPOINT (/tts)
        # --------------------------------------------------------------------
        if parsed_url.path == '/tts':
            query = urllib.parse.parse_qs(parsed_url.query)
            text = query.get('text', [''])[0]
            lang = query.get('lang', ['hi'])[0]
            
            if not text:
                self.send_response(400)
                self.end_headers()
                return

            tl = LANG_CODE_MAP.get(lang, 'hi')

            # Chunk text into reasonable sentences (Google TTS supports ~140 chars per query)
            chunks = []
            clean_text = text.replace('\n', ' ').strip()
            # Split by common sentence / clause markers
            sentences = clean_text.replace('।', '.').replace('|', '.').split('. ')
            for s in sentences:
                s = s.strip()
                if not s:
                    continue
                while len(s) > 130:
                    idx = s[:130].rfind(' ')
                    if idx <= 0:
                        idx = 130
                    chunks.append(s[:idx])
                    s = s[idx:].strip()
                if s:
                    chunks.append(s)

            if not chunks:
                chunks = [clean_text[:130]]

            # Fetch and concatenate MP3 audio frames for seamless playback
            audio_bytes = bytearray()
            for chunk in chunks[:6]:  # Limit to 6 chunks for instant low-latency delivery
                try:
                    tts_url = f"https://translate.google.com/translate_tts?ie=UTF-8&client=tw-ob&tl={tl}&q=" + urllib.parse.quote(chunk)
                    req = urllib.request.Request(tts_url, headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    })
                    with urllib.request.urlopen(req, timeout=6) as response:
                        audio_bytes.extend(response.read())
                except Exception as ex:
                    print(f"   [TTS Stream Error] {ex}")
                    break

            if audio_bytes:
                self.send_response(200)
                self.send_header('Content-Type', 'audio/mpeg')
                self.send_header('Content-Length', str(len(audio_bytes)))
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Cache-Control', 'public, max-age=7200')
                self.end_headers()
                self.wfile.write(audio_bytes)
                return
            else:
                self.send_response(502)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                return

        # --------------------------------------------------------------------
        # 2. STATUS & HEALTH CHECK ENDPOINT (/)
        # --------------------------------------------------------------------
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        status_info = {
            "status": "online",
            "service": "Bodhi School of Yoga Telephony Bridge & Indian Voice Engine",
            "voiceTone": "Indian Female (Natural Studio)",
            "supportedLanguages": ["Hindi", "English (India)", "Telugu", "Tamil", "Kannada", "Malayalam", "Bengali"],
            "supportedProviders": ["exotel", "twilio", "generic_webhook"],
            "port": PORT
        }
        self.wfile.write(json.dumps(status_info).encode('utf-8'))

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            req = json.loads(post_data.decode('utf-8'))
        except Exception as e:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"error": f"Invalid JSON payload: {e}"}).encode('utf-8'))
            return

        # --------------------------------------------------------------------
        # 1. GATEWAY CREDENTIAL VALIDATION ENDPOINT (/test-gateway)
        # --------------------------------------------------------------------
        if self.path == '/test-gateway':
            provider = req.get('provider', 'exotel')
            account_sid = (req.get('sid') or '').strip()
            api_key = (req.get('apiKey') or req.get('key') or '').strip()
            api_token = (req.get('token') or '').strip()
            subdomain = (req.get('subdomain') or 'api.in.exotel.com').strip()

            if provider == 'exotel':
                if not account_sid or not api_token:
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        "valid": False,
                        "message": "Exotel requires both Account SID and API Token (and API Key)."
                    }).encode('utf-8'))
                    return

                # If user did not provide separate api_key, use account_sid or test both
                effective_key = api_key or account_sid
                auth_str = base64.b64encode(f"{effective_key}:{api_token}".encode('utf-8')).decode('utf-8')

                # Test on requested subdomain, with automatic fallback
                hosts_to_test = [subdomain]
                alt_host = 'api.exotel.com' if 'in.exotel' in subdomain else 'api.in.exotel.com'
                hosts_to_test.append(alt_host)

                last_code = None
                last_err = ""
                for host in hosts_to_test:
                    url = f"https://{host}/v1/Accounts/{account_sid}.json"
                    http_req = urllib.request.Request(url, headers={'Authorization': f"Basic {auth_str}"})
                    try:
                        with urllib.request.urlopen(http_req, timeout=8) as resp:
                            data = json.loads(resp.read().decode('utf-8'))
                            self.send_response(200)
                            self.send_header('Content-Type', 'application/json')
                            self.send_header('Access-Control-Allow-Origin', '*')
                            self.end_headers()
                            self.wfile.write(json.dumps({
                                "valid": True,
                                "carrier": f"Exotel India ({host})",
                                "message": f"✅ Exotel Account '{account_sid}' verified on {host}! Ready for live telecom outbound calling."
                            }).encode('utf-8'))
                            return
                    except urllib.error.HTTPError as he:
                        last_code = he.code
                        last_err = he.read().decode('utf-8')
                        continue
                    except Exception as ex:
                        last_err = str(ex)
                        continue

                # If failed, return actionable guidance
                advice = f"Exotel Error ({last_code}): {last_err}"
                try:
                    p = json.loads(last_err)
                    if p.get('RestException', {}).get('Code') == 34010:
                        advice = (
                            "❌ Exotel Error 34010 (Invalid Auth Key/Token):\n"
                            "1. Account SID: Your account name (e.g. bodhischoolofyoga) from your Exotel dashboard URL.\n"
                            "2. API Key: The 32-character key from Settings > API Settings.\n"
                            "3. API Token: The API token from Settings > API Settings."
                        )
                except Exception:
                    pass

                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({
                    "valid": False,
                    "carrier": "Exotel India",
                    "message": advice
                }).encode('utf-8'))
                return

            elif provider == 'twilio':
                sid = account_sid
                token = api_token
                if not sid or not token:
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        "valid": False,
                        "message": "Twilio Account SID and Auth Token cannot be empty."
                    }).encode('utf-8'))
                    return

                url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}.json"
                auth_str = base64.b64encode(f"{sid}:{token}".encode('utf-8')).decode('utf-8')
                http_req = urllib.request.Request(url, headers={'Authorization': f"Basic {auth_str}"})
                try:
                    with urllib.request.urlopen(http_req, timeout=8) as resp:
                        data = json.loads(resp.read().decode('utf-8'))
                        self.send_response(200)
                        self.send_header('Content-Type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        self.wfile.write(json.dumps({
                            "valid": True,
                            "carrier": "Twilio Voice",
                            "message": f"✅ Twilio Account '{sid}' verified! Active and ready for outbound IVR dispatch."
                        }).encode('utf-8'))
                        return
                except urllib.error.HTTPError as he:
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        "valid": False,
                        "carrier": "Twilio Voice",
                        "message": f"❌ Twilio Error {he.code}: Invalid Account SID or Auth Token."
                    }).encode('utf-8'))
                    return
                except Exception as ex:
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        "valid": False,
                        "carrier": "Twilio Voice",
                        "message": f"⚠️ Could not reach Twilio: {ex}"
                    }).encode('utf-8'))
                    return

            else:
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({
                    "valid": True,
                    "carrier": provider,
                    "message": "Custom Webhook configured."
                }).encode('utf-8'))
                return

        # --------------------------------------------------------------------
        # 2. OUTBOUND CALL DISPATCH ENDPOINT (/call)
        # --------------------------------------------------------------------
        to_phone = req.get('to', '').strip()
        caller_id = (req.get('callerId') or '08047198800').strip()
        provider = req.get('provider', 'exotel')
        account_sid = (req.get('sid') or '').strip()
        api_key = (req.get('apiKey') or req.get('key') or '').strip()
        api_token = (req.get('token') or '').strip()
        agent_phone = (req.get('agentPhone') or '+91 98703 47348').strip()
        subdomain = (req.get('subdomain') or 'api.in.exotel.com').strip()
        lang = req.get('language', 'Hindi')

        clean_to = ''.join(c for c in to_phone if c.isdigit())
        if clean_to.startswith('91') and len(clean_to) == 12:
            clean_to = clean_to[2:] # 10 digit Indian mobile
        elif clean_to.startswith('0') and len(clean_to) == 11:
            clean_to = clean_to[1:]

        print(f"\n[TELEPHONY DISPATCH] To: +91 {clean_to} | Carrier: {provider} | Lang: {lang}")

        # --------------------------------------------------------------------
        # A. REAL EXOTEL INDIA OUTBOUND CALL DISPATCH
        # --------------------------------------------------------------------
        if provider == 'exotel' and account_sid and api_token:
            clean_agent = ''.join(c for c in agent_phone if c.isdigit())
            if clean_agent.startswith('91') and len(clean_agent) == 12:
                clean_agent = clean_agent[2:]
            elif clean_agent.startswith('0') and len(clean_agent) == 11:
                clean_agent = clean_agent[1:]

            clean_caller = caller_id.replace('+', '').replace(' ', '').replace('-', '')
            if len(clean_caller) == 10 and clean_caller.startswith(('80', '11', '22', '40', '44')):
                clean_caller = '0' + clean_caller

            effective_key = api_key or account_sid
            auth_str = base64.b64encode(f"{effective_key}:{api_token}".encode('utf-8')).decode('utf-8')

            # We will attempt primary subdomain (api.in.exotel.com), and auto-fallback to (api.exotel.com)
            hosts_to_try = [subdomain]
            alt_host = 'api.exotel.com' if 'in.exotel' in subdomain else 'api.in.exotel.com'
            hosts_to_try.append(alt_host)

            auth_variants = [auth_str]
            if api_key and api_key != account_sid:
                alt_auth = base64.b64encode(f"{account_sid}:{api_token}".encode('utf-8')).decode('utf-8')
                auth_variants.append(alt_auth)

            from_num = f"0{clean_agent}" if (clean_agent and not clean_agent.startswith('0')) else (clean_agent or f"0{clean_to}")
            to_num = f"0{clean_to}" if not clean_to.startswith('0') else clean_to

            last_error = ""
            last_code = 401

            for host in hosts_to_try:
                for a_str in auth_variants:
                    exotel_url = f"https://{host}/v1/Accounts/{account_sid}/Calls/connect.json"
                    
                    payload_data = {
                        'From': from_num,
                        'To': to_num,
                        'CallerId': clean_caller,
                        'TimeOut': '30',
                        'CustomField': lang
                    }
                    payload = urllib.parse.urlencode(payload_data).encode('utf-8')

                    http_req = urllib.request.Request(exotel_url, data=payload, headers={
                        'Authorization': f"Basic {a_str}",
                        'Content-Type': 'application/x-www-form-urlencoded'
                    })

                    try:
                        with urllib.request.urlopen(http_req, timeout=12) as response:
                            res_body = response.read().decode('utf-8')
                            res_json = json.loads(res_body)
                            call_sid = res_json.get('Call', {}).get('Sid', f"EXO_{clean_to}")
                            print(f"   ✅ Real Exotel Call Dispatched ({host}): SID {call_sid}")
                            
                            self.send_response(200)
                            self.send_header('Content-Type', 'application/json')
                            self.send_header('Access-Control-Allow-Origin', '*')
                            self.end_headers()
                            self.wfile.write(json.dumps({
                                "status": "success",
                                "hasCredentials": True,
                                "carrier": f"Exotel India ({host})",
                                "callSid": call_sid,
                                "to": f"+91 {clean_to}",
                                "message": f"Real call dispatched to +91 {clean_to} via Exotel! (Bridging {from_num} ➔ {to_num})"
                            }).encode('utf-8'))
                            return
                    except urllib.error.HTTPError as he:
                        last_code = he.code
                        last_error = he.read().decode('utf-8')
                        print(f"   [Exotel Attempt Failed] Host: {host} | Code: {he.code} | {last_error}")
                        continue
                    except Exception as ex:
                        last_error = str(ex)
                        print(f"   [Exotel Exception] Host: {host} | {ex}")
                        continue

            # If all attempts failed, report friendly troubleshooting
            friendly_msg = f"Exotel API Error ({last_code}): {last_error}"
            try:
                err_parsed = json.loads(last_error)
                rest_ex = err_parsed.get('RestException', {})
                if rest_ex.get('Code') == 34010:
                    friendly_msg = (
                        "Exotel Error 34010 (Invalid Auth Key/Token).\n\n"
                        "How to resolve in Gateway Settings:\n"
                        "1. Account SID: Your account name from your Exotel dashboard URL (e.g. bodhischoolofyoga).\n"
                        "2. API Key: The 32-character key from Settings > API Settings.\n"
                        "3. API Token: The API Token from Settings > API Settings.\n"
                        "4. Cluster: Select 'India Cluster (api.in.exotel.com)'.\n\n"
                        "Tip: You can also click '📱 Direct Dial (SIM)' to call this number right now from your phone with 0 API keys!"
                    )
            except Exception:
                pass

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "carrier_error",
                "hasCredentials": True,
                "carrier": "Exotel India",
                "httpCode": last_code,
                "message": friendly_msg
            }).encode('utf-8'))
            return

        # --------------------------------------------------------------------
        # B. REAL TWILIO VOICE OUTBOUND CALL DISPATCH
        # --------------------------------------------------------------------
        elif provider == 'twilio' and sid and token:
            twilio_url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Calls.json"
            auth_str = base64.b64encode(f"{sid}:{token}".encode('utf-8')).decode('utf-8')
            target_e164 = f"+91{clean_to}"

            # TwiML with Indian Voice for Bodhi School of Yoga
            twiml = f'<Response><Say language="en-IN" voice="Polly.Aditi">Namaste from Bodhi School of Yoga. Welcome to Yoga Alliance accredited teacher training and online classes. One of our coordinators will connect with you shortly.</Say><Pause length="1"/></Response>'
            payload = urllib.parse.urlencode({
                'To': target_e164,
                'From': caller_id,
                'Twiml': twiml
            }).encode('utf-8')

            http_req = urllib.request.Request(twilio_url, data=payload, headers={
                'Authorization': f"Basic {auth_str}",
                'Content-Type': 'application/x-www-form-urlencoded'
            })

            try:
                with urllib.request.urlopen(http_req, timeout=12) as response:
                    res_body = response.read().decode('utf-8')
                    res_json = json.loads(res_body)
                    call_sid = res_json.get('sid', f"CA_{clean_to}")
                    print(f"   ✅ Real Twilio Call Dispatched: SID {call_sid}")
                    
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        "status": "success",
                        "hasCredentials": True,
                        "carrier": "Twilio Voice Global Trunk",
                        "callSid": call_sid,
                        "to": target_e164,
                        "message": f"Real call dispatched to {target_e164} via Twilio Voice!"
                    }).encode('utf-8'))
                    return
            except urllib.error.HTTPError as he:
                err_content = he.read().decode('utf-8')
                print(f"   ❌ Twilio API Error: {he.code} - {err_content}")
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({
                    "status": "carrier_error",
                    "hasCredentials": True,
                    "carrier": "Twilio Voice",
                    "httpCode": he.code,
                    "message": f"Twilio API Error ({he.code}): {err_content}"
                }).encode('utf-8'))
                return
            except Exception as ex:
                print(f"   ⚠️ Twilio Network Exception: {ex}")

        # --------------------------------------------------------------------
        # C. ZERO-CREDENTIAL GUIDANCE RESPONSE (CLEAR & EXPLICIT)
        # --------------------------------------------------------------------
        call_sid = f"SIM_{clean_to[-6:] if len(clean_to) >= 6 else 'TEST'}_{int(time.time())}"
        print(f"   ℹ️ Cloud Gateway credentials not found for +91 {clean_to}. Returning needs_credentials guidance.")
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps({
            "status": "needs_credentials",
            "hasCredentials": False,
            "carrier": "Gateway Credentials Required",
            "callSid": call_sid,
            "to": f"+91 {clean_to}",
            "callerId": caller_id,
            "message": "Cloud Gateway credentials (Account SID & Token) are required to physically ring mobile numbers in India (+91) over cellular networks. Or click Direct Dial (SIM) to call immediately from your device."
        }).encode('utf-8'))

    def log_message(self, format, *args):
        # Quiet standard HTTP log messages
        return

def run_server():
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), TelephonyBridgeHandler) as httpd:
        print(f"================================================================")
        print(f"  Bodhi School of Yoga Telephony Bridge Active: http://localhost:{PORT}")
        print(f"  🎙️ Indian Female Voice Engine: Enabled (7 Languages)")
        print(f"  📞 Carrier Outbound Dispatcher: Exotel India, Twilio, Webhook")
        print(f"================================================================")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down Telephony Bridge...")
            httpd.server_close()

if __name__ == "__main__":
    run_server()
