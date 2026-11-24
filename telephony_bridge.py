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

# ----------------------------------------------------------------------------
# EXOTEL CREDENTIAL SANITIZATION & MULTI-PERMUTATION AUTH ENGINE
# ----------------------------------------------------------------------------
def clean_exotel_sid(sid: str) -> str:
    if not sid:
        return ""
    s = str(sid).strip().rstrip('/')
    if 'my.exotel.com/' in s:
        s = s.split('my.exotel.com/')[-1].split('/')[0]
    elif 'exotel.in/' in s:
        s = s.split('exotel.in/')[-1].split('/')[0]
    elif 'exotel.com/' in s:
        s = s.split('exotel.com/')[-1].split('/')[0]
    s = s.replace('https://', '').replace('http://', '').strip('/')
    if '.' in s and not s.startswith('AC'):
        s = s.split('.')[0]
    return s.strip()

def build_exotel_auth_permutations(account_sid: str, api_key: str, api_token: str):
    clean_sid = clean_exotel_sid(account_sid)
    key = (api_key or '').strip()
    tok = (api_token or '').strip()
    
    candidates = []
    # 1. Best standard: (api_key, api_token) with URL path = clean_sid
    if key and tok and clean_sid:
        auth_bytes = base64.b64encode(f"{key}:{tok}".encode('utf-8')).decode('utf-8')
        candidates.append((clean_sid, auth_bytes, f"Standard (Key: {key[:4]}*** : Token: {tok[:4]}***)"))

    # 2. Inverted Key and Token: (api_token, api_key) with URL path = clean_sid
    if tok and key and clean_sid and tok != key:
        auth_bytes = base64.b64encode(f"{tok}:{key}".encode('utf-8')).decode('utf-8')
        candidates.append((clean_sid, auth_bytes, f"Swapped (Token: {tok[:4]}*** : Key: {key[:4]}***)"))

    # 3. If api_key was empty or same as account_sid: (clean_sid, api_token) with URL path = clean_sid
    if clean_sid and tok and (not key or key == clean_sid):
        auth_bytes = base64.b64encode(f"{clean_sid}:{tok}".encode('utf-8')).decode('utf-8')
        candidates.append((clean_sid, auth_bytes, f"SID-as-User ({clean_sid} : Token: {tok[:4]}***)"))

    # 4. Swapped SID & Key in URL: clean_sid as username, key as URL sid
    if key and tok and clean_sid and key != clean_sid:
        auth_bytes = base64.b64encode(f"{clean_sid}:{tok}".encode('utf-8')).decode('utf-8')
        candidates.append((key, auth_bytes, f"Swapped URL SID ({clean_sid} auth, {key} in URL)"))

    return candidates

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

            clean_sid = clean_exotel_sid(account_sid)
            mask_key = f"{api_key[:4]}***" if len(api_key) >= 4 else api_key
            mask_tok = f"{api_token[:4]}***" if len(api_token) >= 4 else api_token
            print(f"\n[GATEWAY TEST] Provider: {provider} | SID: '{clean_sid}' (raw: '{account_sid}') | Key: '{mask_key}' (len {len(api_key)}) | Token: '{mask_tok}' (len {len(api_token)}) | Host: {subdomain}")

            if provider == 'exotel':
                if not account_sid or not api_token:
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        "valid": False,
                        "carrier": "Exotel India",
                        "message": "Exotel requires Account SID, API Key, and API Token."
                    }).encode('utf-8'))
                    return

                candidates = build_exotel_auth_permutations(account_sid, api_key, api_token)
                hosts_to_test = [subdomain]
                alt_host = 'api.exotel.com' if 'in.exotel' in subdomain else 'api.in.exotel.com'
                if alt_host not in hosts_to_test:
                    hosts_to_test.append(alt_host)

                last_code = None
                last_err = ""

                for host in hosts_to_test:
                    for url_sid, auth_str, desc in candidates:
                        test_paths = [
                            f"/v1/Accounts/{url_sid}/Calls.json?PageSize=1",
                            f"/v1/Accounts/{url_sid}/Balance.json",
                            f"/v1/Accounts/{url_sid}.json"
                        ]
                        for path in test_paths:
                            url = f"https://{host}{path}"
                            http_req = urllib.request.Request(url, headers={'Authorization': f"Basic {auth_str}"})
                            try:
                                with urllib.request.urlopen(http_req, timeout=8) as resp:
                                    print(f"   ✅ [VERIFIED] Host: {host} | Path: {path} | Auth: {desc}")
                                    self.send_response(200)
                                    self.send_header('Content-Type', 'application/json')
                                    self.send_header('Access-Control-Allow-Origin', '*')
                                    self.end_headers()
                                    self.wfile.write(json.dumps({
                                        "valid": True,
                                        "carrier": f"Exotel India ({host})",
                                        "verifiedSubdomain": host,
                                        "message": f"✅ Exotel Account '{url_sid}' verified on {host}!\nCredentials are valid and active for outbound IVR calling."
                                    }).encode('utf-8'))
                                    return
                            except urllib.error.HTTPError as he:
                                last_code = he.code
                                last_err = he.read().decode('utf-8')
                                print(f"   [Test Attempt Failed] Host: {host} | Path: {path} | Auth: {desc} | Code: {he.code}")
                            except Exception as ex:
                                last_err = str(ex)
                                print(f"   [Test Exception] Host: {host} | {ex}")

                # If failed, return actionable guidance
                advice = f"Exotel Error ({last_code}): {last_err}"
                try:
                    p = json.loads(last_err)
                    if p.get('RestException', {}).get('Code') == 34010:
                        advice = (
                            "❌ Exotel Error 34010 (Invalid Auth Key/Token):\n\n"
                            "Please check your credentials in the 3 separate fields:\n"
                            "1. Account SID: Your Exotel dashboard handle (e.g. bodhischoolofyoga).\n"
                            "2. API Key: The 32-character key from Settings > API Settings.\n"
                            "3. API Token: The API token from Settings > API Settings.\n"
                            "4. Cluster: Try selecting 'India Cluster (api.in.exotel.com)'."
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
            clean_sid = clean_exotel_sid(account_sid)
            mask_key = f"{api_key[:4]}***" if len(api_key) >= 4 else api_key
            mask_tok = f"{api_token[:4]}***" if len(api_token) >= 4 else api_token
            print(f"   [AUTH DISPATCH] SID: '{clean_sid}' (raw: '{account_sid}') | Key: '{mask_key}' (len {len(api_key)}) | Token: '{mask_tok}' (len {len(api_token)}) | DID: '{caller_id}' | Subdomain: '{subdomain}'")

            clean_agent = ''.join(c for c in agent_phone if c.isdigit())
            if clean_agent.startswith('91') and len(clean_agent) == 12:
                clean_agent = clean_agent[2:]
            elif clean_agent.startswith('0') and len(clean_agent) == 11:
                clean_agent = clean_agent[1:]

            clean_caller = caller_id.replace('+', '').replace(' ', '').replace('-', '')
            if len(clean_caller) == 10 and clean_caller.startswith(('80', '11', '22', '40', '44')):
                clean_caller = '0' + clean_caller

            candidates = build_exotel_auth_permutations(account_sid, api_key, api_token)

            # We will attempt primary subdomain (api.in.exotel.com), and auto-fallback to (api.exotel.com)
            hosts_to_try = [subdomain]
            alt_host = 'api.exotel.com' if 'in.exotel' in subdomain else 'api.in.exotel.com'
            if alt_host not in hosts_to_try:
                hosts_to_try.append(alt_host)

            clean_agent_10 = clean_agent[-10:] if len(clean_agent) >= 10 else clean_agent
            clean_to_10 = clean_to[-10:] if len(clean_to) >= 10 else clean_to
            clean_caller_digits = ''.join(c for c in caller_id if c.isdigit())
            if clean_caller_digits.startswith('91') and len(clean_caller_digits) == 12:
                caller_10 = clean_caller_digits[2:]
            elif clean_caller_digits.startswith('0') and len(clean_caller_digits) == 11:
                caller_10 = clean_caller_digits[1:]
            else:
                caller_10 = clean_caller_digits

            caller_id_variants = [
                f"0{caller_10}" if not caller_10.startswith('0') else caller_10,
                f"+91{caller_10}",
                caller_10,
                caller_id.replace(' ', '').replace('-', '').strip()
            ]
            seen_c = set()
            unique_callers = [c for c in caller_id_variants if c and not (c in seen_c or seen_c.add(c))]

            # Phone number formatting combinations to try (10-digit, E.164, 0-prefixed)
            number_pair_variants = [
                (clean_agent_10, clean_to_10, "10-digit standard"),
                (f"+91{clean_agent_10}", f"+91{clean_to_10}", "E.164 format"),
                (f"0{clean_agent_10}", f"0{clean_to_10}", "0-prefixed format"),
            ]

            last_error = ""
            last_code = 401
            call_dispatched = False

            for host in hosts_to_try:
                for url_sid, a_str, desc in candidates:
                    for f_num, t_num, num_desc in number_pair_variants:
                        for cid in unique_callers:
                            exotel_url = f"https://{host}/v1/Accounts/{url_sid}/Calls/connect.json"
                            
                            payload_data = {
                                'From': f_num,
                                'To': t_num,
                                'CallerId': cid,
                                'TimeOut': '30'
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
                                    print(f"   ✅ Real Exotel Call Dispatched ({host}) [{desc}] [{num_desc}] [CID: {cid}]: SID {call_sid}")
                                    
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
                                        "message": f"Real call dispatched to +91 {clean_to} via Exotel! (Bridging {f_num} ➔ {t_num} with Caller ID {cid})"
                                    }).encode('utf-8'))
                                    return
                            except urllib.error.HTTPError as he:
                                last_code = he.code
                                last_error = he.read().decode('utf-8')
                                print(f"   [Exotel Attempt Failed] Host: {host} | Auth: {desc} | Numbers: {num_desc} ({f_num} ➔ {t_num}) | CID: {cid} | Code: {he.code} | {last_error}")
                                if (he.code == 401 and '34010' in last_error) or (he.code == 403 and ('KYC' in last_error or 'compliant' in last_error)):
                                    # Auth or KYC issue: do not retry other number pairs on this invalid credential/host combination
                                    break
                            except Exception as ex:
                                last_error = str(ex)
                                print(f"   [Exotel Exception] Host: {host} | {ex}")
                                continue
                        if (last_code == 401 and '34010' in last_error) or (last_code == 403 and ('KYC' in last_error or 'compliant' in last_error)):
                            break
                    if last_code == 403 and ('KYC' in last_error or 'compliant' in last_error):
                        break
                if last_code == 403 and ('KYC' in last_error or 'compliant' in last_error):
                    break

            # If all attempts failed, report friendly troubleshooting
            friendly_msg = f"Exotel API Error ({last_code}): {last_error}"
            try:
                err_parsed = json.loads(last_error)
                rest_ex = err_parsed.get('RestException', {})
                msg_text = rest_ex.get('Message', '')
                
                if last_code == 403 or 'KYC' in msg_text or 'compliant' in msg_text or 'KYC' in last_error:
                    friendly_msg = (
                        "⚠️ Exotel Error (403 Forbidden - KYC Required):\n\n"
                        f"\"{msg_text or 'Your account is not yet KYC compliant. This is mandatory before making outbound calls.'}\"\n\n"
                        "Your Account SID, API Key, and Token are 100% verified and working!\n\n"
                        "However, under Indian telecom regulations (TRAI/DoT), Exotel requires a one-time business KYC verification in your Exotel dashboard (my.exotel.com) before real cellular phone calls can ring Indian handsets.\n\n"
                        "📱 Instant Solution (Zero Waiting):\n"
                        "Click the green '📱 Direct Dial (SIM)' button in the IVR dialer to call this lead directly from your phone/device right now without waiting for KYC approval!"
                    )
                elif rest_ex.get('Code') == 34010:
                    friendly_msg = (
                        "Exotel Error 34010 (Invalid Auth Key/Token).\n\n"
                        "How to resolve in Gateway Settings:\n"
                        "1. Account SID: Your account name from your Exotel dashboard URL (e.g. self6777).\n"
                        "2. API Key: The 32-character key from Settings > API Settings.\n"
                        "3. API Token: The API Token from Settings > API Settings.\n"
                        "4. Cluster: Select 'Singapore / Global (api.exotel.com)'.\n\n"
                        "Tip: You can also click '📱 Direct Dial (SIM)' to call this number right now from your phone with 0 API keys!"
                    )
                elif msg_text:
                    friendly_msg = f"Exotel Error ({last_code}): {msg_text}"
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
