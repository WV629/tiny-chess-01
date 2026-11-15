# tiny-chess-01: alpha-beta engine, 0x88 board, tapered eval, TT, null move, QS. Fixed node budget, no clock.
import json, os, sys, urllib.error, urllib.request
U = os.environ.get("MAKEFUN_ENV_URL") or sys.exit("MAKEFUN_ENV_URL is not set")
M = (0, 100, 320, 330, 500, 900, 0)      # material
PH = (0, 0, 1, 1, 2, 4, 0)               # phase weight, 24 at the start
I = 30000; MT = 29000; D = 100000  # nodes per move
F = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
# Piece-square tables: 64 chars, rank 8 first; value = (ord(c)-97)*5-50.
PA = "kkkkkkkk" "uuuuuuuu" "mmoqqoom" "llmppmll" \
  "kkkookkk" "ljikkijl" "lmmggmml" "kkkkkkkk"
KN = "aceeeeca" "cgkkkkgc" "ekmnnmke" "elnoonle" \
  "eknoonke" "elmnnmle" "cgkllkgc" "aceeeeca"
BI = "giiiiiig" "ikkkkkki" "iklmmlki" "illmmlli" \
  "ikmmmmki" "immmmmmi" "ilkkkkli" "giiiiiig"
RK = "kkkkkkkk" "lmmmmmml" "jkkkkkkj" "jkkkkkkj" \
  "jkkkkkkj" "jkkkkkkj" "jkkkkkkj" "kkkllkkk"
QN = "giijjiig" "ikkkkkki" "ikllllki" "jkllllkj" \
  "kkllllkk" "illlllli" "iklkklki" "giijjiig"
KM = "eccaacce" "eccaacce" "eccaacce" "eccaacce" \
  "geecceeg" "iggggggi" "ookkkkoo" "oqmkkmqo"
KE = "aceggeca" "egikkige" "eioqqoie" "eissssie" \
  "eissssie" "eioqqoie" "eekkkkee" "aeeeeeea"
def tb(s):
 t = [0]*128
 for i, ch in enumerate(s):
  r, f = divmod(i, 8)
  t[(7-r)*16+f] = (ord(ch)-97)*5-50
 return t
PS = [None, tb(PA), tb(KN), tb(BI), tb(RK), tb(QN), tb(KM)]
EK = tb(KE)
TM = [None] + [[M[p]+v for v in PS[p]] for p in range(1, 7)]
# TV: value of a signed piece on a square, white's view (mirrored for black).
TV = [[0]*128 for _ in range(13)]
for p in range(1, 7):
 for s in range(128):
  if s & 0x88: continue
  TV[p+6][s] = TM[p][s]; TV[6-p][s] = -TM[p][s ^ 0x70]
Z = []
_s = 0x9E3779B97F4A7C15
for _ in range(13*128+16+8+1):
 _s = (_s*6364136223846793005 + 1442695040888963407) & 0xFFFFFFFFFFFFFFFF
 Z.append(_s)
z = Z[-1]
B = [0]*128
T = True; C = 0; EP = -1; H = 0
V = 0; W = 0; X = 0
WK = 4; BK = 116; N = 0
TT = {}; P = []; R = set()
KO = (14, 18, 31, 33, -14, -18, -31, -33)
GO = (1, -1, 16, -16, 15, 17, -15, -17)
BO = (15, 17, -15, -17)
RO = (1, -1, 16, -16)
QO = (1, -1, 16, -16, 15, 17, -15, -17)
class Sp(Exception): pass
def su(fen):
 global T, C, EP, H, V, W, X, WK, BK
 parts = fen.split()
 for i in range(128): B[i] = 0
 r = 7; f = 0
 for ch in parts[0]:
  if ch == "/": r -= 1; f = 0
  elif ch.isdigit(): f += int(ch)
  else:
   p = "PNBRQK".index(ch.upper())+1
   if ch.islower(): p = -p
   B[r*16+f] = p; f += 1
 T = parts[1] == "w"
 C = 0
 for ch in parts[2]:
  if ch == "K": C |= 1
  elif ch == "Q": C |= 2
  elif ch == "k": C |= 4
  elif ch == "q": C |= 8
 EP = -1 if parts[3] == "-" else (ord(parts[3][0])-97)+(int(parts[3][1])-1)*16
 V = W = X = 0; H = 0
 for s in range(128):
  if s & 0x88: continue
  p = B[s]
  if not p: continue
  V += TV[p+6][s]
  if p > 0:
   W += PH[p]
   if p == 6: WK = s
  else:
   X += PH[-p]
   if p == -6: BK = s
  H ^= Z[(p+6)*128+s]
 if not T: H ^= z
 H ^= Z[1664+C]
 if EP >= 0: H ^= Z[1680+(EP & 7)]
def A(s, w):
 if w:
  t = s-15
  if not (t & 0x88) and B[t] == 1: return 1
  t = s-17
  if not (t & 0x88) and B[t] == 1: return 1
 else:
  t = s+15
  if not (t & 0x88) and B[t] == -1: return 1
  t = s+17
  if not (t & 0x88) and B[t] == -1: return 1
 for d in KO:
  t = s+d
  if not (t & 0x88) and B[t] == (2 if w else -2): return 1
 for d in GO:
  t = s+d
  if not (t & 0x88) and B[t] == (6 if w else -6): return 1
 for d in QO:
  t = s+d
  while not (t & 0x88):
   p = B[t]
   if p:
    if p == (5 if w else -5): return 1
    if p == (4 if w else -4) and d in RO: return 1
    if p == (3 if w else -3) and d in BO: return 1
    break
   t += d
 return 0
def G(caps):
 ms = []; w = T
 for s in range(128):
  if s & 0x88: continue
  p = B[s]
  if not p or (p > 0) != w: continue
  ap = p if p > 0 else -p
  if ap == 1:
   d = 16 if w else -16; r = s >> 4; t = s+d
   if not (t & 0x88) and not B[t] and not caps:
    if (w and (t >> 4) == 7) or (not w and (t >> 4) == 0):
     for pr in (5, 4, 3, 2): ms.append(s | (t << 7) | (pr << 14))
    else:
     ms.append(s | (t << 7))
     if (w and r == 1) or (not w and r == 6):
      t2 = s+2*d
      if not B[t2]: ms.append(s | (t2 << 7))
   for dd in (d-1, d+1):
    t = s+dd
    if t & 0x88: continue
    q = B[t]
    if q and (q > 0) != w:
     if (w and (t >> 4) == 7) or (not w and (t >> 4) == 0):
      for pr in (5, 4, 3, 2): ms.append(s | (t << 7) | (pr << 14))
     else: ms.append(s | (t << 7))
    elif t == EP: ms.append(s | (t << 7))
  elif ap == 2 or ap == 6:
   for dd in (KO if ap == 2 else GO):
    t = s+dd
    if t & 0x88: continue
    q = B[t]
    if not q:
     if not caps: ms.append(s | (t << 7))
    elif (q > 0) != w: ms.append(s | (t << 7))
  else:
   for dd in (BO if ap == 3 else RO if ap == 4 else QO):
    t = s+dd
    while not (t & 0x88):
     q = B[t]
     if not q:
      if not caps: ms.append(s | (t << 7))
     else:
      if (q > 0) != w: ms.append(s | (t << 7))
      break
     t += dd
 if not caps:
  if w:
   if C & 1 and not B[5] and not B[6] and B[4] == 6 and not A(4, False) and not A(5, False) and not A(6, False): ms.append(4 | (6 << 7))
   if C & 2 and not B[1] and not B[2] and not B[3] and B[4] == 6 and not A(4, False) and not A(3, False) and not A(2, False): ms.append(4 | (2 << 7))
  else:
   if C & 4 and not B[117] and not B[118] and B[116] == -6 and not A(116, True) and not A(117, True) and not A(118, True): ms.append(116 | (118 << 7))
   if C & 8 and not B[113] and not B[114] and not B[115] and B[116] == -6 and not A(116, True) and not A(115, True) and not A(114, True): ms.append(116 | (114 << 7))
 return ms
def MK(m):
 global T, C, EP, H, V, W, X, WK, BK
 f = m & 127; t = (m >> 7) & 127; pr = (m >> 14) & 7
 p = B[f]; c = 0; cs = t
 if (p == 1 or p == -1) and t == EP and not B[t]:
  cs = t-16 if p > 0 else t+16; c = B[cs]
 else: c = B[t]
 u = (m, c, cs, C, EP, H, V, W, X, WK, BK)
 V -= TV[p+6][f]
 H ^= Z[(p+6)*128+f]
 np = p
 if pr: np = pr if p > 0 else -pr
 V += TV[np+6][t]
 H ^= Z[(np+6)*128+t]
 if c:
  V -= TV[c+6][cs]
  H ^= Z[(c+6)*128+cs]
  ac = c if c > 0 else -c
  if p > 0: X -= PH[ac]
  else: W -= PH[ac]
 if pr:
  if p > 0: W += PH[pr]
  else: X += PH[pr]
 B[t] = np; B[f] = 0
 if cs != t: B[cs] = 0
 if (p == 6 or p == -6) and (t-f == 2 or f-t == 2):
  if t == 6: rf, rt = 7, 5
  elif t == 2: rf, rt = 0, 3
  elif t == 118: rf, rt = 119, 117
  else: rf, rt = 112, 115
  r = B[rf]; B[rt] = r; B[rf] = 0
  V -= TV[r+6][rf]; V += TV[r+6][rt]
  H ^= Z[(r+6)*128+rf] ^ Z[(r+6)*128+rt]
 if p == 6: WK = t
 elif p == -6: BK = t
 ncr = C
 if p == 6: ncr &= ~3
 elif p == -6: ncr &= ~12
 for sq, bit in ((0, 2), (7, 1), (112, 8), (119, 4)):
  if f == sq or cs == sq: ncr &= ~bit
 if ncr != C:
  H ^= Z[1664+C] ^ Z[1664+ncr]; C = ncr
 if EP >= 0: H ^= Z[1680+(EP & 7)]
 if (p == 1 or p == -1) and (t-f == 32 or f-t == 32): EP = (f+t)//2
 else: EP = -1
 if EP >= 0: H ^= Z[1680+(EP & 7)]
 H ^= z; T = not T
 return u
def UN(u):
 global T, C, EP, H, V, W, X, WK, BK
 m, c, cs, ocr, oep, oh, oevm, ophw, ophb, owk, obk = u
 f = m & 127; t = (m >> 7) & 127; pr = (m >> 14) & 7
 p = B[t]
 B[t] = 0
 B[f] = (1 if p > 0 else -1) if pr else p
 if c: B[cs] = c
 if (p == 6 or p == -6) and (t-f == 2 or f-t == 2):
  if t == 6: rf, rt = 7, 5
  elif t == 2: rf, rt = 0, 3
  elif t == 118: rf, rt = 119, 117
  else: rf, rt = 112, 115
  B[rf] = B[rt]; B[rt] = 0
 C, EP, H, V, W, X, WK, BK = ocr, oep, oh, oevm, ophw, ophb, owk, obk
 T = not T
def E():
 ph = W+X
 s = V + ((EK[WK]-PS[6][WK])-(EK[BK ^ 0x70]-PS[6][BK ^ 0x70]))*(24-ph)//24
 return s if T else -s
def O(ms, ttm, ply):
 def sc(m):
  if m == ttm: return 1000000
  f = m & 127; t = (m >> 7) & 127; pr = (m >> 14) & 7
  mv = B[f]; vc = B[t]
  if not vc and not pr and (mv == 1 or mv == -1) and t == EP: vc = 1 if T else -1
  if vc or pr:
   s = 10000
   if vc: s += 10*M[vc if vc > 0 else -vc]-M[mv if mv > 0 else -mv]//10
   if pr: s += 800+pr*20
   return s
  return 0
 return [m for _, m in sorted(((sc(m), m) for m in ms), reverse=True)]
def Q(a, b, ply):
 global N
 N += 1
 if N > D: raise Sp
 if ply > 64: return E()
 if ply and (H in R or P.count(H) > 1): return 0
 ks = WK if T else BK
 if A(ks, not T):
  best = -I
  for m in O(G(False), 0, ply):
   u = MK(m)
   if A(WK if not T else BK, T): UN(u); continue
   P.append(H); s = -Q(-b, -a, ply+1); P.pop(); UN(u)
   if s > best: best = s
   if s > a: a = s
   if a >= b: break
  if best == -I: return -MT+ply
  return best
 s = E()
 if s >= b: return b
 if s > a: a = s
 for m in O(G(True), 0, ply):
  u = MK(m)
  if A(WK if not T else BK, T): UN(u); continue
  P.append(H); s = -Q(-b, -a, ply+1); P.pop(); UN(u)
  if s > a: a = s
  if a >= b: break
 return a
def S(d, a, b, ply):
 global N, H, EP, T
 N += 1
 if N > D: raise Sp
 if ply and (H in R or P.count(H) > 1): return 0
 ks = WK if T else BK
 chk = A(ks, not T)
 ao = a
 e = TT.get(H); ttm = 0
 if e:
  ttm = e[3]
  if e[0] >= d:
   if e[1] == 0: return e[2]
   if e[1] == 1 and e[2] >= b: return e[2]
   if e[1] == 2 and e[2] <= a: return e[2]
 if d <= 0: return Q(a, b, ply)
 if d >= 3 and not chk and (W if T else X) > 0:
  oep, oh = EP, H
  if EP >= 0: H ^= Z[1680+(EP & 7)]
  EP = -1; H ^= z; T = not T
  P.append(H); s = -S(d-3, -b, -b+1, ply+1); P.pop()
  EP, H = oep, oh; T = not T
  if s >= b: return b
 best = -I; bm = 0
 for m in O(G(False), ttm, ply):
  u = MK(m)
  if A(WK if not T else BK, T): UN(u); continue
  P.append(H); s = -S(d-1, -b, -a, ply+1); P.pop(); UN(u)
  if s > best: best = s; bm = m
  if s > a: a = s
  if a >= b: break
 if best == -I: return -MT+ply if chk else 0
 fl = 0
 if best <= ao: fl = 2
 elif best >= b: fl = 1
 TT[H] = (d, fl, best, bm)
 if len(TT) > 200000: TT.clear()
 return best
def uc(m):
 f = m & 127; t = (m >> 7) & 127; pr = (m >> 14) & 7
 s = chr(97+(f & 7))+str((f >> 4)+1)+chr(97+(t & 7))+str((t >> 4)+1)
 if pr: s += "nbrq"[pr-2]
 return s
def rt(moves, curfen):
 global R
 su(F); hs = [H]
 for u in moves:
  f = (ord(u[0])-97)+(int(u[1])-1)*16
  t = (ord(u[2])-97)+(int(u[3])-1)*16
  pr = 0
  if len(u) == 5: pr = "nbrq".index(u[4])+2
  MK(f | (t << 7) | (pr << 14)); hs.append(H)
 R = set(hs[:-1]); su(curfen)
def pk(legal):
 global N
 ms = [m for m in G(False) if uc(m) in set(legal)]
 if not ms: return legal[0]
 ms = O(ms, 0, 0)
 N = 0; best = ms[0]
 for d in range(1, 9):
  try:
   a = -I; bs = -I; bm = best
   for m in ms:
    u = MK(m)
    if A(WK if not T else BK, T): UN(u); continue
    P.append(H); s = -S(d-1, -I, -a, 1); P.pop(); UN(u)
    if s > bs: bs = s; bm = m
    if s > a: a = s
   if bs > -I:
    best = bm; ms = [best]+[m for m in ms if m != best]
  except Sp:
   break
 return uc(best)
def pt(path, body):
 req = urllib.request.Request(U+path, data=json.dumps(body).encode(),
  headers={"content-type": "application/json"})
 try:
  with urllib.request.urlopen(req) as res: return json.load(res)
 except urllib.error.HTTPError as e:
  sys.exit(f"{path}: HTTP {e.code} {e.read().decode(errors='replace')}")
def main():
 while True:
  g = pt("/game", {})
  if g["status"] == "done": break
  while g["status"] == "your_move":
   su(g["fen"]); rt(g.get("moves") or [], g["fen"])
   P.clear(); P.append(H)
   g = pt("/move", {"game": g["game"], "move": pk(g.get("legal_moves") or [])})
  print(f"game {g['game']}: {g['outcome']} by {g['reason']}", file=sys.stderr)
 print(f"done: {g.get('wins')} won, {g.get('draws')} drawn, {g.get('losses')} lost", file=sys.stderr)
main()
