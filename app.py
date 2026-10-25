from __future__ import annotations

# まるたいスタンプラリー / アプリの処理はこの1ファイルに集約
import hmac
import logging
import math
import os
from collections import Counter
from datetime import datetime
from zoneinfo import ZoneInfo
from html import escape
from io import BytesIO
from pathlib import Path
from typing import Any, Callable, Iterable, Literal
from urllib.parse import quote
from uuid import UUID, uuid4, uuid5, NAMESPACE_URL

import folium
import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageOps
from streamlit_folium import st_folium
from supabase import create_client

ROOT = Path(__file__).resolve().parent
ASSET_DIR = ROOT / "assets"
STAMP_PATH = ASSET_DIR / "tai_stamp.png"
BUCKET = "visit-photos"
LOGGER = logging.getLogger("marutai")

# 公開一覧の取得済みデータ。出典・取得日・設備不明の扱いは検索設定欄に表示。
# 2026-10-25に検索取得し、既存facilities形式へ変換した初期データ。
# 出典: JFSC（CC BY 4.0）。座標: 国土地理院住所検索で住所一致を確認。
# 350件中338件の位置を確認。残る12件は座標をNoneのまま保持。
# データ本体だけを圧縮し、アプリ処理と分けて読み込む。
import base64 as _base64
import json as _json
import zlib as _zlib
INITIAL_FACILITIES = _json.loads(_zlib.decompress(_base64.b85decode(
    'c-qaqTW?+0l_vUEj6BzD%=@L^8V&S$=!XItsE31tgJ52(0;H2hk~)n>;{YOQ*}BUYS(GCwl4Z%3FOnt8wkTPb|8h3>Ci&#QaK>1h'
    'duwg&No&zrGYKkDXwgN9AII$*bBu5NU;q18ze&IPkH69}MkRD1PA5uKQI1&83yHCmU>&uR@?ZVauYTwMdxn2|cV}mI@6*}$-%W3R'
    '2frKrpYp%{{ty2PKJ&-?yFdLNe(QhwKcwzoyu5em!Ty8C({oSZcYR8K$bbAJd}4O};qKF~54N87|BdP8Yt!3*-v8|E^y<~!osGS#'
    '_l4g3=u4)j7azm__iz25e)Fe)Pw*EI>OW|~H5KrizyIC89{w&9?msBUoL2wztAF!<{PpkuNB-Tf{cry8>)`+NZ@>DFzx(&!{&xO}'
    '-}yiN`yc#ofBkR2|I@Gk_&@&eo8SHG;<NuVhd=)2Px;sX{)gYfUlRYu@lU_`f8cBX=@0*&|KEQ)1S?2hT+oKdP!v%?1>(IdL^+#^'
    '<J3gqUx76}`PKBvC$lHtjEU6kFQ@n3o8H{qeR^q*6lZ{xtN|sBV`>d3t+nK~F;FUIS5jg`nGUEVNZ>q^U`hzq8X8>e0d;PB_U)~4'
    'f!f_UGyk$nlVTK2iq(+P)>6BU6j#QH#z+a44Ei7mDh2SrY)BAP6Oofn%F5zH=pl7}Yxl=bCmZ+22J7_xk00!x`(gU<?C#TZhj?+o'
    '%Tx`E8&QEvJ0%;V#Y|x?OGgqHlBiTH#4W8zR>|s;SrMi5(7Ls~_r>PO4tRchZ|map;lou2WU6XcnrXHU6y;L3_CW2G4$ep7V-!Sr'
    'rHFMt5oavZr7%xTFRoATzYE{t^zrp^!P<NAe0KB6?AqPkofC&fC69JOEmQ?8<peX0!OGI-7%8}3QV`8`N)WD$Cr+towKu+`z7u|P'
    'Zu;q0kgb}9_CpU80>Ps7*v@z*wj0h|>m-QAYhsQ>cn&_ub0S`Nv@z~oV8Mek_P~1haQfYaagmzcI=Q=Z<yD}PM>?RQoSTYG2}@n;'
    '6liUNAkGOBS_4cp6US^KDOs*_@Z2)jgX!6o>E*Y_j_PL*KKuHWHR&T^l8mxSKsONRS!0;2D~d-a2t;nkf80}IlNLl$DU8b@Cfh5i'
    'W|tpKzj-+_Oh0}KA1}i>V@IVu1+i0C(jFDIwa+CTf_K6Y=QH?R2@ux<fEIibLP~AnFV{oq+NpVTn(cfsdvtn4toFaZJ-vB*iPg_k'
    '=~_uz2~a{)%3G(tsF_evkz_NN6ouFXb(A13vJ#*|U^LqvSl3^SUQbQ$-04@I90L@up+q5GS4_$<DO#fh`7OjO84=W4qL}0)WS<Ea'
    'TnL&n{6$0$rJExMr@c#e_aB{j#rM$bL=7TtovD-sLh|Odc?yB@0A+!50SrlcPCS!PL+K1OCfF2G-|L=yGue87vh{4T`OW0SiOJU2'
    'ldTUYTVG7J9!<8!bi%zmm!~^l!N<$0sxz=^Q6)8#ZXG@FkLHox2w{^99_oY?fg&40d;$nLExtshqzvp8dV4n>jb47v2_TT09-*;E'
    '1S?r76AZPqb?F%$3&tBtr~rPf6jj6t9*6~)L>7TZ-OGRb+qXv#R(lst1M<_04_*~iM@Dtdtl<@BWSx~Y1xn_SqSTHUr!cBR<g!Hu'
    'BB4^x@Qd)iXHEy7fABYA$p*m^b(&m@?O;{fwlAuT&!rGct%0J715JjsM+yXXVN&FVs~%QAd^b8)`wzdIzIZhK=IN^#g=B_T$qf7j'
    'YvrfZ+BOgIP@K!eHOU6ZvC2_HmCo=Nr=U(KP#2q5Nd5He)a>S$KRr9W{8r}`7KD4qWYc@&cV=dvTw9?!7D24KrUVpSt%t>$n_Grd'
    'oQjE1a9N<w(ou-?3D~rBOi&<%!SuU*XRl8-zL;#Be=}0|rnm3^3`~cgUVcIG|DF24!GF!Vg&E`4!7)bC=Dh{WO!Nv!vfyB5Dltba'
    'I46n0LY((qJG<ZD+nAlWJ{B^w?K`t;U(dccJAH6*_t|w|gL{{rDnO{Co~sZ!Y8k6QWRz*`geC$)8qkp;Ln*2qCr*L=Fr!UmIxAqz'
    'y*g|A4!GI$-KS%rwEKLE0VcX?IY5HfLzA%r>gC3$c&D;qh7;yBaK2z5h+82cQUyn)Gn@;%!uh6;ei%gf2HH;d1<|D>{1=Ue|CbeX'
    '=HE*XnOEO>JJOOx^gPjddrk>1NpPN$Sag=rIUD-@-`SHhqj}PkGYcExYc^sapX!S1IAxj}Nf9yHAPDz@V)-bEqoM#~Q6;z}xlq06'
    'a&YFv^y%kgVKV<}2n*wNT%?q|f(zwNHtzvsDu7#)pbM1MK0r#65u+~TsFb~=vR463Hcm}8E=@LW41ng~-3vbl&HU4|hc~7dZ$lOr'
    'hrYws&;gU-Le^eU7;7DHrHM&L?n!h85;hAK3myn9L3u7yaYE)EI-9qU(r(_u@3Z?3$H8dv)#PE?=Ia<yQ+w;x7IH*$zM*Xq$~q#E'
    'bSQjf@)62I><K{Gz$Ht*kI^?B)xSKN1zp2jjeaE!+R%Ew)<RbrY?kWgF91ddCJn@!;DZA50Yh>rDN>w<AD9=>7~P*4I5DU!9*E1g'
    '&-QPf#h@e5W*A-fD=KO>qlFc%qfU&)<-i?D*#Pfy8i+)Z9#Xaxi3S=nFMVLn?Ei3PK)xOX4E#E~`~-nftPTvLmR16el2*6w1tre1'
    'WXeJ<BcKRY+7KvU0^xzWLXCt%*!6+wzNfCyKdhn|W;&N2>^}Xd0|!G66YB^uW@?O`nbs~P1%;Sg0?|w|w44BiO*RBdi=eQoVcfnB'
    '&>Wh#rnkS?yYrW^{A>O}m$GQxj3@viYCUT$TAPtiCW99z;-G>c%A^QHGc!_h%0NK1iYr8O<IeQy<JtG$jb=cLjD=a9VOU-_A!<d%'
    'ge=C(<|f1gSPIlQ(G{HJ^27pHAmHF8ilAs&8BV(W`SgQxV_D7ot3kr*9IFZp6SUGflvc^sQJEJdDLye$%5heUY2uBeBw0?Aiauo4'
    'AB6ySdi#(_y#*!VWaI2)^Ymo%ol$_=KYM3-|2`rlyY#gV6IAY1oG4O^w$p7)%7Q^U76#sx3nw-SMnnYv(uFFT%*s>jh}ml%o7KXv'
    ')+<4#SnZ*VGTJ&cdtU;Sn-Yv>{t85i10y0*6dSQ#Hnz_>uiQhw8Zsd{I3NSv>i9RS5()Ub30Zj|)10;TEaM?jsX{SpaU3!dB$#9g'
    '<vG}7X$(rOK{Hawc~$Ssaap$*PHPcIS=!uWobbuXWJu)E19#vSd8i^>s{loE(Z;Kl*3F0o^7Q=n^x^{~4uV!YT2?Yy%in-jYfhCc'
    '*oXvH4k1MlB@8FtTL$1bs#D<LNpa<69=n%g5r;+c?p(>$IXPogR!U^+WOKerO~~1rNSMWuSqQ`gX)ZCIQx>huD+7D8os+XGcSf_B'
    'XLt54-8kf%=uNfuu&i|}jA=j5k)#*GKqX@WJ|t_2gLx2-EfiaxGN_tOudvxW`T2<6G>^Vw;Z1rS7pqJS7cP18VOYy7&?iH5^cwSZ'
    'AXZBS79)(;+$Gi@-9Py1%HGY*adDB0I;PUO!RCFfyQQ1IxFm=p+y?ANWF(tZ5GSn#mcW?QTn3tYQRYAY^MC&5|MD;Y?Vo>oc51Tu'
    '2>-M7(PZo1PtQ(c<+m{;l~2!YABoufb9)!gPVc?<s;9%drz(E%=L>)Lmbwp+r3<HoNA7@ADNUSpo`_7j5FVnBVXt*cA5Atsev=`+'
    '8I#$M*U^?9UuTCwhp%%@X&qnpE+ecl&0k-Vi^4j>qJwZ811CVlDG??oVCpnRTKce@*}HK1ug7Hn``ddj@Z$~-Rqs+*@S+MRP`%66'
    'sBqyqRD6u^oV&daOMK1-hwyo^-00j-;FHa_CmUZ*HZF`{EY~06)9Ce2mJRi_j;PVn8B;M9Mw>r3SQa&o7ZO=CCCVB|-r8i6xDvrR'
    'Z?d+l&Em~l-LTl#lg%f<EhiiA%zqurr;tQ3G$On1Q__gaYZa$XH*Zl`&%IZf1eSm=WLHQ?83zv)XC8+IXuqev_0DALtI5_Uvuj^X'
    'pKkq?&`e)$@1NW3Oh<Puz;(ak6&eNR!&z(QZE{Q^1TdcjHUxFCCKkXTR{EHLV<oNh>Wsjx>wmpZ%^hm@$8V<>ZY;Z^>zQ10Lru+I'
    'XmeZ=b*?A{C5=qLqo^&!7NFh=xE1hAD1VAuX=xq&_`zR~%kIvZuFg5vk*GT9HWI>3#fzk+x^+EFg<_^yLjW3ly(>@(JDd|x+;f#|'
    ')Ry&Ed#=wOjggujo|!)S!7hrIO8C`aw-rQaM>iWkNQo3&0Ee*{R|HQa1YWQYQKI$U3%|C%Gk_!v0Oih0C=qveuDr_E>v09#$5x)f'
    '8Mm(ayGt(IM@UIV;6pEvHHaxR0{?c9vVmyQ*azm@FGfKHzRv9N_fYC~&a>`2R@TOC4V0Uz^{85i%DKQe(K#Am*$yKLRfN)<QxZ<A'
    'l_vR<M*})m1Iqt9f7yTVxSOS6^_tF5SuJ!q_;PC+sYMJrL$RU+!)8^4<O3`qWSb%OM#+Ld?z+SPNG?6t`|2CaI2{$*d$KXR`F1xj'
    '|J6SPElMUs<(3&SF=R+RShSezNz}y%FSF0KKl{I^yGCJ)%dfV4XIhW8QVCTt7;c<xoqw#3LS%~?0iD4>$>Ni=gxVZbViA{;D$wlR'
    '{dWKS;}LmdH;iTKF&Bq6Dsy{Wa?`viUQCIh1X3c?M7aWlnnzs31>Epc(emR?^dBe0bm_TLu^6r@a}h>R(VR9qDw*+7lA;wyO#n<o'
    '96RG#C8*;<5V8kJS80q@v2<uur-F@UOji=K)J!#hA%NmpL(U;kxj-ILIgr33*i6zqIKiQ6>4lerci*2~xiNx~bZw}k-)J?Xyy7)N'
    '!2h&fm(9i+F9azPtV21l6C0c)E_)wLpp538i5y(}c6$4ZgIjl}?{9X*`TqWyhktEc`TqXF<qzfIlxJn|!CF(<Qh>_4wXxt^zNAzW'
    'ZY_?Y;Q)lEK%0fJRF&eb>(Rr5Pp=+4x-)(FaKPxyF`{iZiYBV{oOG-<T`weSK3L?V2PgKP6qd2^f(i%HNRoK~t5HctE04SBa@^LX'
    't+!b)*;GJ*ywo}aWl9aRA>eRK!IcAs!Yhs#@Z<;_5xAr8FSXqL>Df0wJ^OCCt2o(si3=5*XGWj`UDrh{*pXY$N)9r0E#y$snhT^-'
    'l3`hs9Dy(@DJgNTFv629ETx=se@1wA`Pq;bZzs@#S{g^<()%}%D7|_Us8%xC0R^ZOdPXVR{JAzmmJX1%p+ZnZWr)s>Qb%YiEHYoH'
    '=qo+UZk-(BT*m?ksv0B;cmA^b^7<i6b}a<`J?H^&qT;nTKo5*13YUbf7l}wHzcUL^1iK!wUY5Q;Jv%l3mVSD6dQ3Zd=j8m$VmzwO'
    'rD-TQYE1~Oxo+LX(^PQWWhEMdG*Ju^nN2K^SfJ8!NrxnO|0(6$$;Qpe#tVo)Xitw$zqS9~puWV#2lz^GBwmY8&u%`Me!J6oo2Zj<'
    '2;8c=3T2yb<wpS(V2lh`5g{g_%$NsqMG{pCCoj3>v@)4L+1l>j5^hg6pUk%Jjf2zoC-={vUQU9l%Aj?%T69u2Uj~Lc2>375%h^UG'
    '6v2>?fvh_gQ8=VH<!FCg_VnJpvt!xM{HrbPr}FfzM1^PJ(|qebDAex~YUM(lO#(8Sio`~ZGmlU&TBE66k><I1dv@c|8%xB2us}ST'
    'UB9u|6<cTITvVT(9Hjc@8f!&x3pEkRT57DHfovJ=h>XrN!6?hY9Welkq7GOJeK^_p0Slrx%U}$4uWmOJeg<r@Vz&;Ns;zh!ho;op'
    '!K9$5(m*&xS;(w$lL{cCko9PGJo%Na)nRW8#|qG5Ij3K-CC)3Oea3RtToc66A~}<u@M0kHNYm}w0Wj7^6LR9Qn3bo7-6tnUOkQ&@'
    '>mH_LZ5|1r(WX*QJ1W{wgEH?VHG)V*BS6C;D2HH43`WMJT>?`7OI~4yn#~tyr#HXji-FMfb`Lk&uIDRY&|I``fU%+(<nBahz@DIv'
    '0?2#FB$RG`m@+R{tmfrtpy1TwnZv2a&YMhSP?pyynB~n^76Jsg<S8RX8n756po+#^UQ&`e<HJPmzsBrbpI&`F8ZupZ14g43J=1k('
    'qMX(^yk(~OIH*awKmt!h<Zjgkp`qClrnK-y74JfCMRRuP$%v^5DxAsIh5ct=^5q&(B{?}qtJPn7LLq4cvSk@zDFUIeR)IG`hLXjI'
    '0@Wu?S^NUMfWa~N<ksAH_|dg7kQ`d6c7RW-*60)!WDtOfQ{EGmd?7v<L$rw{L3W~MWhnpZ$K!gGT)bITCh{$-@hYcebCp4stb?Bj'
    'ai)`N4oIsYHK}BzDm*e3S$`n^^ucFej|I!#SJ$985{p@q+9G&ulEf+2{OPyg!ef$&1W4WJNT@rNDdAS7ka!BVuO2YFb{&h>kzncc'
    '%kJ?-1GSQ_rL4`9K<%rVk2$JHDQ;u3jKiNL11?Tk0;w`Gjbm!AH~hKx?nmQA-ZP8!!a60OO4p(;zWX+R#B)YL0R=^GOb*+n1qA~&'
    'F;wVMbaF-XjAifR=d%ajjTdt7fW5Gzm!J%%wpPOcXK8LMTrev#gjyA$h*2KcrIry=64bmla%ox5SoUAs1%f$x5!1crbw$kbw<ep9'
    'ae{L5)5+FF><n$a&HfPvE1ah?7Sy_n3NeG~&!e`DWI;zIA?8qX>=&C~RP&i578kk{y{`Bpn{&(TqZBCuODH-3OYp!Fpv)r<svVJh'
    'q{gOxqx9o$8vonL<{PE7rXOyg#@~?uEj~TH{rTaFyyUemj;6xZMy$Dz&9_r=r^Q0#@e#LxAVU$WBp?(c#ANPhb}M@dL!Yn)BC~(z'
    '<tuPH%URzAqI12-^|?0JTt+e#E=BQ_NM8)9BSLVd#Ucx*Ca5B0l>N!-OPx;XlhM)Xp3dh()~~~(oU^rr&XjG=7<`GqW+^2(Fl<d2'
    'sQ(yMB+BHp%Mf+?Gj6!t^y9JvIBei;AW*YYJNrMJ(aSNNbzK*#tg0<{7}|dS+h^sxBzAs^LZG^W2qXo;gb|ri!Cwby|L&FP%kM`+'
    'XL}o|+QkQQvA(dr?M#`iZNE_NcxxvM-j?7K$6V#`(GLKk-IfRSp-`%o^eb0Q=HJ+{bUFq{>cv-owNADM6~m5bWxh#B-h9&|`4F@f'
    'Bo_`9G)kESnZW-%*EvHC5c}f4)Ayc0<vThwuZFVM&4^P~8xWLKu-2^0C1B?!8B%nC3drk(T`x~KGchr%JS%Ett6}fz)v>VIeR^*H'
    '{jPB#>-k;US{==G`(_}7VIC|H3g(bxcqWL28k!`hwBo_Y5bZBG!ZA4Zbo=2D(%9ilvR(HlCY7x&-ZkH8Wrik~xg(5n+<&o@Se(b`'
    '=EiA`!Nq<%u*))sYJUT!z>bx?7CYkW^$&x;R^{cB+2-;|vAgI|Aifx67FmPsK*|KPgyAJ?9UNbgF4?<uqe;^0qK&QS{F_>|p-PG7'
    'SzR!bMN;5a6jfbN>n|$`^vki7m=LkQb2qzkW5jA_?oj&BVAe+}flg>%TaBTvd4oM<Z6%JO@W>J__!cl3RtUG*gBd%T<cbyres4pj'
    '`;W!6y5!BP<uYK?G0wG6Y;E%if8}_{QZph_=T2OM%>bL=P)`_??GSw;I=lDT{-y7y4=yfePTxX#iUHl9p;&cadZF&jD!H83_KAQl'
    'H^1_efe+h46OjoO|FCclF=rAjPe$9w`3h1Gz8kXyJiq;lbk)TWl>-M?)$z*aqf7<<WXd5Dm+nrK111qD#N=q5wi=KTqBnJc405Gf'
    'zJGsu<HDHybXhHT{bpIo?poJ2YP4)V;O&bxk!nqfbOtv%DRHbsA}n(*GM;o_p{&~mxHDqQXZqc|<!tL!4=(0aaAB(XwjM<dUr10S'
    'F`OL4Gl|wv+{sD>I9Q}orWJ(~lnfdzcb$0!O?9M63#n@2;LOS90|iRDBvDDp6k2dJ7te;E3Jjx`dzGBgVnv>!ld;=)BRIG2{_M=@'
    ';?sEA^y$`8xTDgImvo&*SWcVkcIX^6>TVP77!=A$XX2Bign@epT4a!XMfmxn$;QRW=IOD3nccZJee!6rL{fRbG2I-_>%c(e-28a0'
    'a6<ZIJxLbdDKx~FP<SB4=n#4E(X2I4UraV`k7hF62Mev|$_tL*N{fokFxI@@2?-b+cMk0Z4_IXICQk9uFUX9bF=kfANvAI!jq6JK'
    'aI$@UkAz!Mg+;f&Iv2dun13MXVg^?(6RV)i$x*57M9yGDeMbHi*Y*aK$U}YU`orma@59&Bi*Ywrfk&!JI}jp`6Roq8i#~YVYJ{=|'
    ';9(GcQBjl#4<LE!Sx7xjK7H{C-isN@YVcgvg&Rv<GFy4ZQkAt43k6v7;cOjUF*2Z?<b?9zQ1}UNaUKQ5Ad<E#>W62ZVefCzBON5+'
    'G1P$Wez{npt}oXB0k5SgCX8y`1Qeb}8EGWice^z<5NE;FsOG-FPfz-ln<tA$h@YOFntyw5Tp$^0NRQuN-1w-7+liWJuLabaJD1|d'
    '@hl240UOA`#!1l15UR428R|a~dnGX*@Z7mKZmQ~PzIqlHvNo~<&QF^^^a1^r9J5rXa0gVu6VGWUxf%_Ng=N{FHaPzQ@Wavk>Dt$`'
    '(<c^7SnCrzRA^Znu%)KC;;KoOM<z6Z9|2}?jLHV0kBLSF>Ox_$=T7^Vzn<=VHJZ6}NlGltrKY?O5vArwPBa&F&RM!Z14_|qsQTb1'
    'M7;8l$RqPC%A8dHiqOH;A7>A?#{vfaaj}4ZgqA$hs-n4NIXBHu$=hNn6AVm5W8r5taBg8FiIBN8*TH3*j;o$IIOu+L7829)k+Y`h'
    'Or22`i_wZT->u@sWT^NEPq`bkK)F?Efh<I!6l31>kHZ}N_%`+<#&V_GUmnsYCXblNmKBXZ%M^F5NrF?_O5r16R6<$PNqR6`7mh3i'
    'V-@_58zw9Iq8r_LbC>=0=RXVD;?vXf+uf4MIj9I1k28F2t5F%}YF8GmQte53N&={FBHEUOGE|wkk|AjU=Y;$&BmB2dJvUKzf57a{'
    'P=IcKKKu0k{+*X%IaXlS;Q>BXYjY{yd<-{JVWOm(6ag4Pf_K==$wUVwHKeZ;$_hN+boTQ#7}Ai(y@4PBJo_Jf3m@yHMB-YfU1=p$'
    't<!FmZCwy*=NV17CQ>xM*8oTN!J$ZY)=UB$=KaO1$>uvhJ^xE@1oGMZn;QqJ?n`xcr0b(j8Y<-4OQ><Sz1B`KF3AoU3&xZ*ahhe4'
    'LJs&j%KVDP<~f`MTPQ!g)iuP<Ve{t=2QP+Vh4PXo?;UJC=7)20Yt^(;T-J6anC#w68xIw-Y;6Wwk&MHb4rODIP+W^5DUQFZ)GGp('
    'QFg4rv>LW$bs$V(2h7!UXAEsl!c1n`1G|Wc;>~3RBtB_IvJ+H!MPpe}n(V@Clb~&@n`;oWWo^Jofb+GE*+9RXkI9n6P-8^`_3)?^'
    'ZA8i`1>lFuu0nI~)3Km|-|2;*>MVxRLR2*tO><-t!_(zB)Pzw;X<T#6f)firEgOaPzSz}m>$BUV8x3E~p;qc36#A_h4b!r@{;^3y'
    'C`XdTj$uHF-^dFwDFXLUUP?+=p&9U6JiJPLWi+N<A}Yu0qJp$}Kg<InP)1P5SPmsz4bZU|IRP_H)Ju;y*!s{QPZ$xJd5&U>37+*('
    '0|~vhrNx<SzF>kkj$~1I*)=ny@QzrEHz|{}$$O~CGGE=rA1}`AJvy;aF0HkhRlOdRQ0O#Y>2tQ=Dt>o$5{kkkNJzj{i{qsjs0U-e'
    '%RFSI`dHQ9A}duQuVk_+Jt>+~cWMpQ0<uuxP}6`XVbdKVap2ZuS3)*nMcsC1L>3A`cWx}Nrfw^xo~dh4a@~9dAVnTHhuF)d_5|C@'
    'Bq$VcDz-#nG&3TsE>w?~u$SEGXf++B@jhp*3TDlZNNd5V4MpHSHJFW!otPCRDO0G;O$2QG%Jk&){r7QFXVjz(LHN~vUxj&g+pz10'
    'K-x=2gUuS?myo3uj%z2BTSuILAc!1{_LlaQfUjH_H)$VS{Sur?EeOJTX0kx<D(BxE<@9fGkCSrbOEe=iK|p3oT9BB7<cTw<m^kib'
    'rehOJaio5Ol0cqn<E5;9C^npiQZ%pvjRLRM7Q9(6v8XAs1bpP{3&ef(WJGB8UOYdn^H_bh6swt<<cH+CdEPG4g#_O|kODwQS-f+W'
    'cqB3cB8jmOa&PW-@9VF3cTVhG-I?9}WW;FvswKgz=c|--s%AOVDAD{WD`!(ESEQh#nF2Q=C=f%ypOa4v&yR~$fS#V4-P|70eh$9B'
    'hF|U4UA}zNs!(rM87$Sty5=*t4$LJ{mWhZc=M_CAUX};|d0nhmjxqllK$pg~pe12gG_}@GS1D;UueAW3X}(~jq%VvDdGe^zuA&UY'
    'd1gr|#VKEe)qPnV+=%|}&X}Cx#;xhaPnXcty2!l3z_oKmH*fffAR^U;#DJQwS$g8(PbE0f&hgexF+Jy+7j0uU+2>zy^$y&6^ijI1'
    'JH#wC&DSEF)zLyc_6E1Gtgu)nGm?yx3MIN#|MhSF{p@{qaZDny>{86LSEW?e)K)K8N!EHvjXI~34VGw)PZ2!hr5V&QFd-_5*F$w*'
    '$^NrP2R9y#&agV8kw;{9VQcJDDA)XfG~1K{YT<boaWn;TmZy;3qc=Y3<RweJ?$-X7FQ+?O(`Oq)<S>TD<#XH9AD)75&F2l)BahX*'
    '(#6r(VsAcg5Q^lHbHa*(f-s2)BunA?QO-fb|1s8|H`sbUTA{pic6VpzQ1@Tdaly0W6%JwX_*rX@Dh02*3gWWGcCjnO3!6z{jOrMp'
    '70&l}AI^_nD2wHTXC;ekRxOl;R?YWkG?)g%3p7RLd0W&A4?dLwEy;UFbMC(ie~**wZ^mYJ`CXjLISQNQr>Ez)4nBVyia@nETU612'
    'vz3VgqqLE-x$Zv|NpK1^Ae4V<K7~s&NuAyf%{E7R+{<u-k-7c(^pigy*#JZ-q8coMtLEEiPRmkqBs>|st|BzCsu%))As$MSlJT@6'
    '(S#d&Zywkl3e5ZqE(*Vj{+lwYc5lTB-aI!!(HVfd5fQrRtMGlCdxDP++Gc8H2&)%px?4_fs`~~bbM-!gb8%kQh&nn_)Mo~?Zmu5V'
    'bv7D>0wwCed5JF!yr9knWOS+VSlaq*#SgnX_jaFt^ag+)Oz*$^8GsHy4PR>iz30>SPAvhlm0>}qYRTI=*L)Kqd!--_6Ar8n4-7gI'
    'EQOD#XS#?CJgYw^u=DQp$#-uKH^ZR89nU8xcVEtrjnto~3}sB$7R-feK0{$>HZgNa5=W&{3Gv23MkgsNuQDsZ8|=#R3|{Mb_T^ac'
    '?CzYITh7lYEHY8kjL|r--Q2ZYa2eP0GMW!+O#&;2EG`{Y$!95rTu~mny!X+$v7o`B)k_Z!KKmL1{32b6THw*5O2<|6A>6DZ7cOd|'
    '6J>ag5!j}+3}qYwl{zu+R;5q|oWUCGS38@)r649FU$FI~8B)q>NS4j*h9!aaDRDAM5al53cx@Q`V}>*uwdegN*DxA2*rlF-yt}gj'
    'u&C;~y;DM0=e2C}vM(!z=bbFcxO1;?T+(CNN3Fs;jfGN1S6`~`znn*hW2t%lqS)h(7;&erA_@o8$~9L-u|_~*FTgQvH!^8~Ja~?G'
    'Seyfnu2bM)MdD(>?7&cH<{vE2kgw~UIpeBV?3rtR+#m+;C9a4R8pYwfZ8U-S0C@|Sr={xaN58p)bG(oPUl7}WYVV^jr`I0*{RKG<'
    'gcBU6MRovI!XbZC%SniibES%P{o~^UWX6Z0fv@77_wd7Y>DnH-V!HOqz?*l9fs<H;I<DM;X()kb>M5`)88hWj^GP3jscG*WAX1OV'
    'LIz)u?>wJg-#kK=o>5jiEeA<LHt*I%53v@-#VPV`JS``bCkZH~Dk(B!`;SwfT^u#qo}Jr^Tuzv*hg;5^t-Xdz(SE|ji6n!NgmaD>'
    'oDnZHhCoboC33K!lGJgZd<TcyOHaCMU{C-4r_r1&5K>Xa)=@n71s_2M3?#7>Bvf~?$k!iuPw!ngJt7!DwGYmmz_PA-iHP!UH++4T'
    'r2XZB=y?V|^`v+l&X+9Dbx66;3gT@Rxj*HIi&bwvt8<KSJKO$Z?=HTs@I}jW{o&H!6Gu&fls9JsMzA1b0IuY7H#sbTE2%`HmLXXy'
    'y(yxydG^-)TO7G;nagrjs$YPo#tCTik&>c$&N3+yl|?xQ1+f>%05MRIXIp|vsz(X_kAMEJ|MK7d(|`S!|MNfnJTTW!@9undG%$-#'
    'W2t-o$8I2i9<fVrSw%ldGu-)a-kwQb_!J=IpaxDdNFxC#C7sR1M(ce4YTm||ow~{WH|@9##Rhox^qqH5|Ki-XIC7>001~nSkkq`n'
    'z!dc%@!~RaNYvtr0Z-*A!njbb&|-p@D-FKs{U4?uoSST1nrwVH**yQ&^u0j=dLUr4Q}5w3`1ObE$gwtUUAHy<I$FZE-=K1ZJCh@E'
    'k~yM^R8R|Rpx#oO!m@Xz|01>f^dp?07zr7Ctn0p@T0GWOZp%ObQZ+|wu9>JrC@L03ib49Flpz-Q0lx66B!o^h@ngTb3`7RZ5t1QW'
    'NWrYHOdI7YBU@TQzHJ?U6ht3vlM~@B5K0b|J7j~s8;VQQj%DtTyYey=7i3ZAf9y}sR&EI6z07rJfJHP{^)=EZUy>t5cPD1>Bqbzy'
    'APh1n8y%&#56y#%@QsZH&FgVl@FSY%wiaomb<HQWghVcxD1i!xK}u(qcmpXcc^kM_ECd^m-Q_zrI_I~S2fEk0!>Ha-q2N-{=97>v'
    '@+`f8tYvX0$ni{EOq^&A)w9Snss3~3?DD(QbC*YUt8?4SsfkLZ434!PaTJ7S?wa2Tjy4-$m=;_c+=@FWl?4PKNLf(sIDD4sxAyS6'
    '8ZCR@I(hK!x#dHhskHWZje{%7n_s|n%y<SxALMRS8VFGG1W4l~sTf2~6b~`>aQWogi0NrDO2VpQ{0@agE1*DjXr7)zQZffljAnSV'
    'R2LEy6GUW@O1J;gUpwqh-rk?xc|JccKKtVAfC0$kXYqQbGF-75O0NA#NeU6-4T?tEZlKTO2`6TVP6fAPm<y`6=dt(si7^Y}Pqv`!'
    '>*|`C@c{Xjy7GuXo684T?QPBwf)y<VDjRA@(4tcW6vDAmLNKonqYrsS7>diauQB6&`)oN>A}ZoaT2xGiOVc`gN0v-1;8K|-oX`Tl'
    '@-%|Q6k}yBV6&;0y$`Ou+<pGuWa|ff0$82|K_$tNd~5y(;G5>T?N`F$70o-tE4Cy!YtF19(<sHyAp9td&I!ki1&3nULSa~JGQO{K'
    '{MpC*+qYYkJL)k0)aEF<Ioa32(Ns5&(lRGJ5$_2g(hU?dg5zA+Lyo3!MO~1;K)H5y{Uu&TJ{q6HPtQN-%H$&iS{1jtvV+G&`>WeZ'
    'QDZF7P3iG|vOqb3ZrN9wER$rO$(74!cPAU?Cz}_i8+WEp9}h}j!$87=2J<1Vu3BE_=3w8ZBC=#0YhL;oh|5+1mk=mjt1|rJvO-l8'
    'L3Pp;K+~)GzMF4PHa;B7e)itM)0KOdo{A%mwo4&u8&&X=ZT*zTg`w~RfH<wOJve{L1FA(`g5rlcuYFkQes#yuPER&JoNRnCqI0pu'
    'ByA;&0o$w{-T|}GtqsRYt00jl;v-&ru+bCeu{ntM>~XMynf{>h=B>%*H{Gv4PBvdmwjPaw&~#^K@9J%EE^)N@n`Wvqj-zdRfqv^_'
    'R;pwaLB^I~VW<tQ2vQvmHN2I5O_M`>w%(s?eLdNH0!eHfh|X`LdmS-nB5AcN=v?a(QI{yAa}aV2D%n~uh{Z>o=)Hh^7K6!sU2#O^'
    '@?`7F$<}))eSPxuNDlU}yXw<zRViKfF(oQ$LE6IKvN=XfM4;!HL|Oz<URdHdRMkNV2fV|18&(9yhjEL6(A<0*aj9>_ASRUw3w$GO'
    '-u#j#2o9AXiB5s_1eU?6sE4={Jy3OPDD5}DP7YCBAM8sn9_{YzEb03CB9+1JPOXWdx|<JenP_GlGL|NZS<F{j;glQH${}i$s>g$;'
    'Jz!2<AFyOL*ji4#H@(&M1LYCGSgtBp&@^|txgMFc@I#Tsk>Z6RN=FUApd3z+%0QO#v41CJdgjKE=ktNU;MVxX`NMgA<JTCcStUI|'
    'IZs=saIcl;&L*OPr$FsjAen0(2<4EpBKX;g+Q86<nSri!`}1y&_S3GssY?7AiB}9Nq1OrBdh>$@S475j7-diokr}LRC}G-iPdRd$'
    'cr2Zu;auU&tFo{DFoUWyHSLb}>c`2-U_4aA@Drd!IhpW5m=dcqiu$SSLVthi+b>2;Nc-R4o__LYy;$&FCz=Mlx%N;lT>DKJldRF4'
    '5y>>p55xeD1i$10F<HVt7uvsF@b=Z&jSok3q^^tnw3A#|?@cJJYU*rMSl<4;G!xbbK?3hCw+rBw!3d&*x9}OoQvX28z#;3Qu)N%!'
    'UGI(*@cO=;v6U4~ZB6sl)kv9Vol<rd5vn>viRYazg=N7@VB@YoUp?q1-f@iO!VN6!WNmf9bjt%3I$%|EJ}FGLLYY7y?iQlJq44&v'
    'Ax0(YsEaQ3Cui}f#q+;Rwk}RKKLfHfZs=W}HLJ9<bj6u4Su@+br;h8G66(1UP^AqAt|POA$(*vLPWqKO(XOvDt~0U4V|cBK0fuX8'
    'a#FPY7)6dY$`nbl!XYq<1RwCInJ+RIsPuGxT^i`%-S>B&Y>$?j&fb|_yW17MuHJ%xa-lYm&X{cNR@#&txO4>SIVfb9@Fd{PKxYJV'
    'Mp-NP`cur%E6IcH=gH23OjfEqNSda)NG4jphjZg&$O^YP46bD=4&LQ);jWt<m0X!VINu?`o?d-E8Z6g0cX!UBM+s3a^sE%TR_Hm?'
    'JlvFsvRV;J8hol!kN}8{0-wZ_V_ZwRB07sBwQoM6c$_Tt@F8jfU3#jja=b?3!+5o-QLU>Qo(kkCnMpA?UlLd#HUphZhL$7>4Z+0Y'
    'Ub;A51413X_*QCQO>4bQWoh$<o>u`%a9;@RI-Us#g3nO#m5_if1z*gH(mq~mxP!L{2CU0JyfHhq^K<7n`~L<$w%oqYkDT~3)Ye#~'
    'HLCrQ6l$Uo9vHUg6gTF9S~@Qk@j_^amxwGceT;5THqQ>JiH`-){;4O^n<x0uO)PDNaFqjR%Gu^sp!NwW^HfL@0mye$SnqHYV1QC0'
    'vf`M2?Kx`Wivc%3j)xHLG(NZp^p!38HnkIiC@ioJlH=|B!U`9idEvx5fr1_0U<9&6QoNTUawu*^c;R;UGWBG#b!vICVN83v^K$Q-'
    'o73+uETzdR%i^p;D{xl3`B_2mEY3s}#5-Ye$QBjmlPB7`!gc0K_La$?G@QQN8rzy)OdtKQIAK~5s1T;INRL~D%~drG3(VuQf{uaW'
    '72reyzQnlTpvEX*<F@p{xi@++nm&1Sc#2%sH)jl3j;-8olEOAuI5wJF&PpK8c^qRhU^^CSAm)PLiAPg>U!&s5$J0BHTEuFz7$#lU'
    '8ZcJWPN8YXBx}C#AfqtW69!m7GSgr;N?GD%5F(^hR9_l<_s5Otw>#sa^D5PwdZq^>u9yy(b#sm5C^aN|z(pFI4dhTMIy@~68LUL_'
    'Br~PoKfXAAnqMZd#n{q%5e<K<+L2&uWb?xf9L&XMG#SGq-XzGx2hIugCMknsC$T@^|K8~#-HcxldE}9DnqWP(TG~p@o6C4`s1k96'
    'g3v5+h|&T&o(dvLpaFN1Lto5ydhNmfrSC^Z=iK((diYXNb3HUmCMwcO*2?aTRa^hE1&?!T0>lCkf`Cjc9vTYT!e<hbt2c)3U!PsS'
    'GqQgzKGsJlX8%35sFU=Pd1pv+ILMBtO+!qHm?VvoG&#{PpP?+lQSAXzZpX8o^M|%`^g(;hDt!$w9Nv5;Fa#b-$(iu(IF-$Ugl_#)'
    'o0M$|8pwSQp{H-p?mQnoHt+77c~vqWp|)-SqRNZ81K(=CaBd=t29;Pd&%jf)@_44o5;U!l9e33BpD6BqHhTQQck?9$tDnm=g38Lu'
    'xi#9d<_rv~n+$P=nAnXZ1EsgXjtOTm>!hS|$JgmU9zb*Z!Dqka`HPBL4sf3J0?08gc=Pc<o}4qu5tB8hFeafe)SPf@DRo8I=z0av'
    '{>7664&?ok>QFAa@?2JwB^j;Nhk`TJeDuQ0VkjrY;;;^$unI94B5lMsI8-9-t&QxzcrbnZs73v=T&1o|{Bu^3TC%`OEpL8x2V02}'
    'YG#%MQN<KMCo&QZl+M{|s$x90;KeUM$1M6kq7t5E<x-v%)-_iXhfH21MGgAmIc}O4sG?Dlib|&N6E^i~pMxL18=ti=szY;l;;Ry!'
    'r4+n!*4;YYe6A^jtt1hFii!dNaf_FUAboiSIbTLrXn)NSXSO%aPBuRrf)S9ap984-G(KNE`l0JUoBF0BleIJ59Kt|z-UWZM4h1q*'
    'mJW|RWbiSSNm1O#L{)bE7q7|I*~!+O$=0)hvl#;cf?p3lelCt?7TVBS?PIBHf4x)|<^=5ygCKMFjsZg0qnF7$Eu;f--0z8<-+g*+'
    'Tx|AkZrbjZz22RN{NQT5l<DTnj;bgt1IL~7hy(3d7Y1M(F-IPq%9Q2aLe2E@H7K4(^Q!aP0E}F!*}BRWsGz(Ol4*0vL|uXxhg(+$'
    '*l4oEDwl~-G(a#e-1Udq@p=8>!?AGLeR=}oa@Rq1)fF04F{@0NTEV4lF8z_XW)#Z4EU``&0m>ZaQJg+dBa&l~<d40JKh$8(p~2`y'
    'fn(R7xn%9EgB9AgZ}4b=DT?B?CY)KpLk1GZo&=6%ut0U_t0!K$Gh&39rzf-2ZjiP7#9b}I@a9A8MP@00ArKm{^27HnhgX_7l|sdm'
    '4W)hYhQ|+4as6;Dw%Y|74W;g@@x#u0&3JU}QZmX9wZ_P49b@s1Kq3IAawdaQfoBy?qZd{y-5(&_JNFX4skb0ZjA%piFUl5ka_h0!'
    ')?}D0V@9-gEt5PDl!*Oyl!HTMMMoJn!-9^C(!#l0yJj#}^8U+pu*YS~Vx5q~k498j0~MzEW0nd5ph=YAG#buVMktTL(R^Xn1EG>M'
    's$bHw7=+8G_jh;BE}lSH#ha9=WGIRY)UBx|jh5L?tP8MF7W~LcV@RR~(tva-#n;cmo!fnKa`brIz0l~|^dR_>6s}4aXzM<gOgv?g'
    'HGw3a@mz8ss7gwxQ!Gn}(<=9jW`Fzk=#}uRS=@@)8&#_IG|ZX@nZUp<Fv!rP@!Fzb#B=R{DHJ10lq#+qgd5zx8C3A?oSxo!&JJh5'
    'Do?`BRWp-oe|#us-z{_z<VnCTA?$iz3XvlCP)efS%GJKjl{@2-%0=v5&q&&cTEm7q+8maM$3|H6L<f}MWRRBvas=SGT7>B1%K5j0'
    'Kfkm4WNTb{pbkTCr5E8?Mc2dPji%-*F(PnPfMgrvq1MBZN)LZ5iLPX4pa_+Uzb0LAcCvBmjmYer?bJ+;LT2&lLm^4Q>TFU;T~nH;'
    'TC~Q6$5M21g)n@&Qxej(XUgFe3dEH_z3BJ%c7ObMZ@?nwKv3}A<-(0_lB>Ftr;TE+CRJfo^SYO1Zj@7k0L|w_sceV~G!kv1PzKkb'
    'lc=mK{`BnB?vI~NPMn-wySuw{2EM(Yo}C^MtmR$B3Ru)smy85w&0FYJPzzazNQWzFB^hE-d>ych9x4iy96$C0`B2Z=_<r`yrRg^>'
    'm%1?P(BS+Qt6k%Ctab7hMd^eWq?J+{TUj_efC`*ItE8kU`94FKKHZu=crg|<^RK3kY@2IEbwx@DC-IsKo>07n${8hD;?AqLmROx4'
    'F;qkzn1)o@8+V&sda{4|n-POCU%b>+VzH>I4Y>9%;U(}CpsFF7d5<D65|1Ja!lC@mEEmg+>o4o!x3l;4lj$daUYw2@aQR{&M)R-B'
    '4^w$9G}khg2L8}|s=|7vGfRp{lM2e6;0ZxUUO=aSB^Y3sV(t2Pm(A}@HqMV`L*0R7cH}`X;0xB)!ZB^{TQ)|+e9=VMjHlp?2bu}2'
    'Q_7;Gm(eIrk9z@laLjq~$z<~(e7ro&ZYrdKirS_TDor+5Ibo$Z2*Og}<p=8nw)`Z@`RBxC4yykY4(w<Dhd0mr?|kz!xO{VX?cv?`'
    'cb{Iun^jluGrsrHmrPGDKK{GUaCz?vWNBQox4<nkK0xsR4n>W#!K*+OJ@$U^8}XQ)-#)nh!Svxn0JsN<_(wnlyu+Gc@L(4vrV?>%'
    '6bip$pu#cOERX%fH2?X2b#{94>-|sOnUA;Oq1(-K-PY0DLwXc%#B2Y|b?gLnNOiVj{}GU4DQgP=5tpe!N`)tPA}}ll-o#VNqCa+g'
    '@bt&&&K6Y3doM1a5p@}BVCQd;L3Lk$cjv^RLE-Hx#{Us;64|nlV<5%qKu{)-_@oN4wm9vj%1N)Bet6y`tM1pu2F=0aC-ChIfC|2I'
    'fcQwXmY<$~!BwMr9V-mg+}Ya24C_qu$rG2DP||tAyvAEa0nCf)LbCEK;U)>|-#8e&oi!Apy~poQHUOS0OOOnLBx@)Ej}SGUDrs|t'
    'DiyrPoAyLFfl3BJ5<C(_c!4UYlQIx)MWJeT<-(hGAcsPPlcn9qORv*M*^yMW1D=Lb(fpN98pR^2$7qM{Cp86xa_NRlMbs+h&<p6('
    '^IJ&Z+j$zTCAzt*$y&3+YDfPD1A@hC)Yd^uQi%%^eBuNU3Wd>-Wq$;2eq4MsKbwDW_39x$3{A+@01`sgPDHron!qXJfgoXsMKe-a'
    'K#}BWAzfcX$%3*($Ca)+wvW9+sLO1$>Sd@HRg2cT`4lAsZVJ&F2)qmtFhZ?P3SO2|E=H*!cwfNuaQNcQ>)1nK!v1rwoWwX}s|Z2j'
    'QhygE9w8YoJQxyE27q|#8Xk%iC7>b*#rx9hk<GU6jb%a8CwR+q8KOJ$;nfJl3|AHNF@`sP8Fk%-XT=DO8q-)roOC3>(r5+(D;-z;'
    'WPbzq)dvLW$KT;?=_4^(e0uN3qrE$S*?s!a^x^}(9OABQ0XSAso>9i>zd?-VITdWL;;gbV6zqpXws*yH;3mmXzM}8?PA6G(eX_L$'
    'zm5VD&Ny9qsu%6Vil7r^HBmIBZ1b~EjMEr6$GH@o{W2*+E|Z#=7;(8@1kt|`i?5m&Zotp_t-1Qlh?cbc(p_taR)^j3E=}#$5pSRA'
    'O`;hJ3P|#%SWIP5R430NRu}KM*Dk7+4fT7o>+cWP*&2=xe!<19qxzzs&`MY8AW2>G6?KO?aXdQW1U`m=H4`r&M(03Lh$Sl1A6UjC'
    'S#SSv*m~W4a&mwu%}|_XpIieIlFNfos<sYU*~QkH+14hcs4p3%oeUaIXGftxAPRU6K6`GtSUs0DeGF0Py-pM2FGy!MA5XSEf0HQp'
    ';K+UH!R*G{{Abj{uq9o)oux$c31(c)Vg`yJVKh-i;F(#x3@<5E`zj>I`)`PkuY;S7Ye8Z;!CVo$H&Rs^)EW{=^Q97>L{SO}J=D@l'
    '<3y_Po;d45=HBJdS5bok25<6=7NENjG(RZDSpB9qX0mDsYQL+6kr+tDJclVD^f>jdNpQgGBa<?V{!Hp8?~j<f<_R9>pHvkVEqP5m'
    'O*+~9m{=%AnCv7Gy5KRf2tg+TN;Z|EBv1_7zkD=%2pRY`hK8}cY5U&p&XuJ?&wA-2xUx0TJt%5hzZ!z$@aTcE7lVgKd@SHrF``>>'
    'a3;Jh+lw-@?@u0F{%|y0I^lL<>zG()YILIguus9KbqO&y<FOjWP=b(YPN+@Ro0tN8dTq{f(9H5sU=A+d0${+Q*dhY2i{)}9DuoWz'
    '7^3+Ts<C+ZsbnbrA|CQFnOLJNk=(Q5P39r=Wh}ez3ZOaIICHSM^VYBhtzW{u%u*<<vVcu1%pItgY94%&FpL#Ji3RqD(&e1k3<aXZ'
    'c|OSE5SV(@YwyK{={GNN1Zb?VeEV~JDw$I+MysJ&DW_QF&ZBIuh#Is{+LVMBvLNU{ej>iaM2ZxqWUw>cKh3iL@XYl7#nDX%gV2$?'
    'H&82A^<t^e!ZtsG$xuE`5hUnDaSgoGh)iNiIz*E!wS9EH{R+OB5&72q3-Y5E{0v@qWwldlrupchRY`@w6KZ16`3(uDWFRbXyc826'
    'nAUOUnvYMgWL?}+Ql%>i9jIyZ<Ru|NrEH1y3}BIr699q}#(7pyfEq6Qt+36Po#x(6yjO#_j-E}nPW>!I`{zISxz+3Cr!jv$?Di<?'
    'EBjJa=z}q+1JQg@z%k<@Be^i#fJF6fJR6#$=3I!Bd2zM9;*IYiHXqy^2cAyy>IKk#xu^<V<(`<OmAOL=DZX_pqhv_%29Nl7r;w%N'
    'B_HE~syknVr@W-}3tqj3qSHyLAUbM!<*~v*t*)$8;F0v^CL}bs%0j&?WkfM%X7TMy;T(`-sepa;$H4)f*}X?2Vl&&mGyC)XgLlt$'
    '39Bl{EQF}kJ4SQbT&X&77hFjmA~8mw#35;+E-FN8;1VVQMC`bm*Mq_7KEPzI+!6gj$!owE*IZH82P;!B1yXo{s@aN2z*G$>o|yzG'
    'OJ-J9pGnVN9}5@MxdJDBesQV%UNae1$yvrx)BFf84}vn;9VH3)$WD=(2S#w&&jVVt^mnhPJJ$y&n;#<*Fa1d@!cB#aQd8MXH<t0{'
    'hNCSIuILp~^n?#Mc;E*QAW0@gq%M2kKl#1*X5N}zK0V;P>@UGdFC47W{Bol5ii0W3wbxQHUb}2Clj9sh%D5kiD_xOisC#T?{b|Ho'
    'CtGAJxwsl%DGGJ%F0s)}Hb1?agXJcJ35kfO6|@BhlXx$b8mgrBQS|$Qz={TRzm5$}*XOA>dlU|9RdP8Pcxz~^Q3+7#bl@TOuqdF)'
    '$w<$GjS<*+j(v`G{`Bm-JEMo?PU1jUtwtzSk&ZLYy7sSqJ_fuJuOs%s1cYX1StccN#lh87WbU{dwZ~87OxLp&ca>Y02F%<vr&vxF'
    'nvw()K`ASN-HQPHoM&G&qsr6RbEbo<-|oG<`KC#gUz)9sM2A*XD~+Y?Z#ydCAflmmdFDv33{LneNM6+X#0=%BKLLI4-H#($O&^_C'
    'ZHx6sJ*aeQ?9)nTnqLiIE&w{57#1NC2Z_c5IV%FEVpb$-`)!M1Cpms`sblK!aO-Hzw`luazyN<r7C;$*MWE6t2Rrft`+<@I?Zky~'
    '``V)I?E!l^`|n>p`1Hlm2rWL1wEX6Y>8W>@@VLrBS*vOqMUFSW5Rf4v%WM+KigLUfMX?BUU_nx6nT0prtljy>Qwo<Ro40;?_Q6lj'
    '-X8@f+|<5yS}bQ&YPZK!<+v;=GPYk~4?;WOo`hzKmmiG;d<rGTs%$xDny*|gd3Ejk>kh4VCtHsOY{DJKqOM*AE1g}t+g(nozvc*t'
    '%&uls&2_JM4jdSkBwjhlX1Ht`jD{i_f}w-|h_G@DX9?HV>B-htldX>?o1b=D21BlO3<YiPtFwDI9+^dctK3wgR#wf+TG?C=i-FHE'
    'sD%{n<rc?@wKfr`6g9H=sEt~YgCCOL2I4Z0O?q*KOVy5D*L1?T(arT&z-UBvKrAAvF+-39x1%zUluU5odfxSKEKDz78zxP23_qJ&'
    '4PS~3R|YU^GM|b%-Z~}~6?26Ae%LU?vymR_M$ckqE<(+iS8nv48xfgTupDvnPZ(R%)sR&3*3P80v{KLjL=>O@im(uT6a~r-v?n>0'
    'O21efJZ^bBf9eDgY<*-GC4_65Bk&h*O}`3mPb8^`E%<KC@KSFUniPjqh8a+!`B-<Ie@V((YErXm!?31dX`2%;$(7b6L6HdMARfCx'
    'sVBxrP&$}`k8H9(&U5O$>9Z^2dXrwxR#u*EpmMFmV8wNFU{qnkP+${28V2MdGU5^{pBk<?4T>>WRyu`vB=X&-<GRz&%&bTzZ8bef'
    '?V8`DO*R+c6g1dOl*v#!GYbDmQDG!0_+0;H@3pU{Pq#+H<^J`<ZU3&fOl#!~tEqd+=AHLslBcNz5|e=HF9Dgbu{a_M=Q;|;itW+S'
    'd0qU|vs3eL?M>n|L-9HI>dK*z@O;{|HlQME=YPPXnoo7x=rSZCLu_Jrg+p=TXaa<!bX12VGBvN?>;=z)I5C#_%-L2a#B$W7XIDE8'
    'Af3{!6SzS2E$}9ybwsJg?o1M+M4J>C_*Tw+)jb?;dhhh;WSuWxiEEu@RXbTH3~#Oh1?FKPMWP@qO1m>Xmo;+MLoN`G7ui26aq1L~'
    'DZhDmXRuRUI5$0UdO2QDdq8)#Ru7x@O|W7-$3blp3m)^Mwh$|QCW&#5=U7GRN1cOr--qxymetI^np(_zxyr;ptDR!gs`=~=YKeHk'
    'BnpNhg_1y_lm})WC@x|{DcawSm~6g1+4#6S32<Rv6TkIpSmpN1p9kyVndze+js|P->FMK755Bvr7Om6@5r>kZ@@Nc+gZ&K}sfNio'
    'U#3;yO#l{r<Wi(I2+j+&ul2&dz;!n4UOX8EoZX!>vxhhLZ*^y}yUEH5w^B7hRD%Ne%_qAP#AcL1Ef$yBqB1B}qlgLchfBtl4Slhi'
    'r<e9mfBQx!8wkzb)%$xNKUWJXz8-rxc9$yK*x+QXxj3iUmtrE(C7_ZTsxBv=NYdECP}$P{GQf1>&h+WyWqWI2VK~&i&Tq}O=XdLl'
    'Sc(+fvC2A|<H9x%($S^lJa)D;P7+E~VGa^1W)&>e2Ixf}r_<+$ycrJ!X6{#Vadv~N>Uuy;XwA^(24swuUgd5J5)!)(oCKMHokQk`'
    '7K*M!>Fat2`**KQUw%KH-E7altXMp$S9bhRe5EGOXK3@&Ek+l{@mzo?3CLE2sAElLC?+Pe(I}SH?*)GL@$At@V_}2yaZBszIC>@e'
    'Xjj{}afUWu<mX_YQBX&c!s8?w?-=I*j2%UXrKB#Ke#h%Rs*#UoHeEJft`=8j4VbMdIttT%ZW#*V5|q|NMvmt<EG2<@%v%vx)SYI`'
    'uIz;l*q1$Cw3%!2i6c+YN~UVyFwUCS%gje$pHh*cAqp#C7Q{ldfsZV;&N5|vUm>;oF^_9B%dsX`iNumtCgX79rnxgksE8S)aswO`'
    '3uZ8y(n%WtD~&0~6vA;gL62uN7+<tJV$@XC7WEBdqWQ=m{7m2vi4ti!&<Ux~V5}y|vaGXl)b@3q0FudxYl{*Y%bZSq?$48r7vqQI'
    'Bdmy9SyMG|c;KaVp#!yqqec)KaM;~*OG41NPwXSl5QOB)h0MF(?w@}=Z-dRht2eg6j>{+5;`&78omf_tu$b#OYg?GK&E5UkkR1de'
    'fp;KLu$je}MSy^9`(@9;XCF^5ULMQY4nF^2|HU)Cco42FB2|Z%@k(#&cN(bqA`}#oM1_4GJOk;0#}g_oqo^An&C1BinaRfa$tL*M'
    'n?v*uk5C)(NOTsTM*q6}0C&H-6xN+tJ>rh25jEarjB0N`OoA`b#0dCWH)!dI%Z!uaL|}N7%!=~bX3|#>kj4UOK4>{TxdjN#2cIfk'
    'W-D!F)KZG(b5DiK$YKI^<#<4SCq}$W8oL?HWtY^-SvKtRY(AR*Ixar58z}e0>vLg>cTzm-hon^VE5?*3q47XcFnIe0iC6dJ2RYw3'
    'Wr2*E{sa2W6GO=8Kx7Us-&$zr(|RY>Kpj?_Cv>d&yO!fpA_gSKjMwFhC)RRBDCT(;L#9QqlF<Pr&_H0oSPm~RNKs$%v%I4JX|c=O'
    '+F-K5jD)dR#EeV)I4TzcVGP1e5;+v6R&jYUnkyY#{{VuqUUa|Ksf01ELd`AwqMPgQM6SFScuN(jIV%ujfDIEWH1`taFf9Ki6Bk2G'
    '=K4c0z*na+X(dBd@3Bd$nm_dg#NQ}MOi6g^kO3`cz7SOk4#GKaOMgS_+fSMV8Cl;RF^pF9Fo5{T=G&l2g8O94N#MAi#WN%)2?X89'
    'C}_!|u(GnAb$Hwm--)|#?~MiW&^o94pet`|byZ)(->PCe6c3QKj>GU5chM)pELMTIi5`-Nuxw-YjtNs(|9t3`3n*kgmQ&q236|LH'
    'T6cXNRvE|Dm3y<s@orhGZDWVJ#B#PoLXsvb6a&Oc0*gqB$z&6cD~jk>ZtOpJJV4rWFgB;VffOODfmjP(X|F?kmd&;FqGmK`>{vL@'
    'aF#n0uNXd`Yvz;*mg)Xh-_?&tV+*gmsJ`k5F|d}MDEz!sd%+6`Cq)n$Q1dJ@OFUkz6I2@!XoS?&U*Ws{V!-*ap}6e6ygs{j_u%q}'
    '>QKUJJvmv*Ev;RD<h1!Ipr|e8Xhx(KsJ&>r#SxtC^2ugOA@-PKZ#N!~8*JZ0cFF49E=8%US&eRg`Nl<BM53N(N+HA;2C)|^Pm&<^'
    'x}0d1rLST2U<ZQB=-gWzEw5uCpi~w=E%w!0mwSqP%B3JeWpF6rEzkq_$UxYoiQ|PfwW@q}ZhN$})P1$(fi_(kTdFnGwRFveb*S_j'
    'r=y7Hcm&8PU<V1P6N4WVi&;x9^h$qp`tE0wjVqJQ55cP@8;`~{9lfaf)|sW{yte%b&^3SNRGJr8Ak6sS!E`v@oG`+XKy8kW7tQ-3'
    '7kd{@j~H<Fet5BW;_EIwnJO;I)m+MQsA$?xl14BciWIvO3ucT!;fD%4MP*4PfMkz*o%nbxVc8$9<ZfBpzPDC1*Wkv@@<LJPBX*ZV'
    'fi75_UI#ofRRThEpIAcmyZ7;r(^FrxNKx}+@s)N2aJY)mFiM-BBZ1n<J0Alv-l75}wn2*)B+8g2R5%a``@7U<?+kg~99r1y+?(FM'
    'Kkp4M*FY-p7%D4zLjVtNK88%4(@}{;gvDzuxK!nUwvkjIOIj4J>YtD}c=!GBi<_?T*`2kvmBui$wZ<@%@2#Tn|NZ|1N6+D='
)))


CSS = r"""
<style>
:root {
  color-scheme: light !important;
  --marutai-header-height:62px;
  --marutai-top-gap:16px;
  --marutai-red:#d9362b;
  --marutai-red-soft:#fff0ed;
  --marutai-navy:#173a5e;
  --marutai-navy-2:#244f78;
  --marutai-cream:#fffaf0;
  --marutai-paper:#f7f0df;
  --marutai-white:#ffffff;
  --marutai-border:#e7dcc7;
  --marutai-blue:#dceef5;
  --marutai-muted:#6b7785;
}
html, body, [data-testid="stAppViewContainer"], .stApp {
  color-scheme: light !important;
  background-color:var(--marutai-cream) !important;
  color:var(--marutai-navy) !important;
}
[data-testid="stAppViewContainer"] {
  background:
    radial-gradient(circle at 14% 7%, rgba(166,210,227,.14) 0 32px, transparent 33px),
    linear-gradient(180deg, #fffdf8 0%, var(--marutai-cream) 100%) !important;
}
[data-testid="stHeader"] { background:rgba(255,253,248,.96) !important; height:calc(var(--marutai-header-height) + env(safe-area-inset-top, 0px)) !important; }
[data-testid="stToolbar"], [data-testid="stDecoration"] { background:transparent !important; }
[data-testid="stSidebar"], [data-testid="stSidebarNav"] { display:none !important; }
.block-container {
  max-width:760px;
  padding-top:calc(var(--marutai-header-height) + var(--marutai-top-gap) + env(safe-area-inset-top, 0px)) !important;
  padding-bottom:8.5rem !important;
}

/* Typography: never place white body text on cream */
.stApp, .stApp p, .stApp li, .stApp label,
[data-testid="stMarkdownContainer"], [data-testid="stMarkdownContainer"] p,
[data-testid="stWidgetLabel"] p, [data-testid="stCaptionContainer"],
[data-testid="stMetricLabel"], [data-testid="stMetricValue"] {
  color:var(--marutai-navy) !important;
}
h1,h2,h3,h4,h5,h6 {
  color:var(--marutai-navy) !important;
  letter-spacing:.01em;
}
h1 { margin-top:.15rem !important; margin-bottom:.55rem !important; }
h2,h3 { margin-top:.65rem !important; margin-bottom:.45rem !important; }
[data-testid="stCaptionContainer"] { color:#516982 !important; }
small { color:#516982 !important; }
hr { border-color:var(--marutai-border) !important; }

/* Buttons */
.stButton > button, .stLinkButton > a {
  min-height:48px;
  border-radius:15px !important;
  border:1px solid var(--marutai-border) !important;
  font-weight:800 !important;
  font-size:1rem !important;
  color:var(--marutai-navy) !important;
  background:var(--marutai-white) !important;
  box-shadow:0 2px 8px rgba(57,43,20,.05) !important;
}
.stButton > button:hover, .stLinkButton > a:hover {
  border-color:#d9a59f !important;
  background:#fff8f6 !important;
  color:var(--marutai-navy) !important;
}
.stButton > button[kind="primary"] {
  background:var(--marutai-red) !important;
  color:#fff !important;
  border-color:var(--marutai-red) !important;
}
.stButton > button[kind="primary"] p,
.stButton > button[kind="primary"] span { color:#fff !important; }

/* Streamlit form widgets: force light appearance even when device/browser is dark */
[data-baseweb="input"], [data-baseweb="base-input"],
[data-baseweb="select"] > div, [data-baseweb="select"] input,
[data-testid="stDateInput"] [data-baseweb="input"],
[data-testid="stTextInput"] [data-baseweb="input"] {
  background:var(--marutai-white) !important;
  color:var(--marutai-navy) !important;
  border-color:var(--marutai-border) !important;
}
[data-baseweb="input"] input, [data-baseweb="base-input"] input,
[data-baseweb="select"] input, [data-testid="stTextInput"] input {
  color:var(--marutai-navy) !important;
  -webkit-text-fill-color:var(--marutai-navy) !important;
  background:transparent !important;
}
input::placeholder, textarea::placeholder {
  color:#8a929b !important;
  -webkit-text-fill-color:#8a929b !important;
  opacity:1 !important;
}
[data-baseweb="select"] span, [data-baseweb="select"] div,
[data-testid="stSelectbox"] span, [data-testid="stMultiSelect"] span {
  color:var(--marutai-navy) !important;
}
[data-baseweb="tag"] {
  background:var(--marutai-red-soft) !important;
  color:var(--marutai-navy) !important;
  border:1px solid #efc3bd !important;
}
[data-baseweb="tag"] span { color:var(--marutai-navy) !important; }
[data-baseweb="popover"], [data-baseweb="menu"], [role="listbox"] {
  background:var(--marutai-white) !important;
  color:var(--marutai-navy) !important;
}
[role="option"] { background:var(--marutai-white) !important; color:var(--marutai-navy) !important; }
[role="option"]:hover, [role="option"][aria-selected="true"] {
  background:var(--marutai-red-soft) !important;
  color:var(--marutai-navy) !important;
}

/* Expander */
[data-testid="stExpander"] {
  background:rgba(255,255,255,.88) !important;
  border:1px solid var(--marutai-border) !important;
  border-radius:16px !important;
  box-shadow:none !important;
}
[data-testid="stExpander"] summary, [data-testid="stExpander"] summary p,
[data-testid="stExpander"] svg { color:var(--marutai-navy) !important; fill:var(--marutai-navy) !important; }

/* Checkbox/radio */
[data-testid="stCheckbox"] label, [data-testid="stCheckbox"] p,
[data-testid="stRadio"] label, [data-testid="stRadio"] p {
  color:var(--marutai-navy) !important;
  opacity:1 !important;
}
[data-testid="stCheckbox"] [data-baseweb="checkbox"] > div:first-child,
[data-testid="stRadio"] [data-baseweb="radio"] > div:first-child {
  border-color:#8ea3b7 !important;
  background:#fff !important;
}
[data-testid="stCheckbox"] [aria-checked="true"] > div:first-child,
[data-testid="stRadio"] [aria-checked="true"] > div:first-child {
  background:var(--marutai-red) !important;
  border-color:var(--marutai-red) !important;
}

/* Segmented control */
[data-testid="stSegmentedControl"] { background:transparent !important; }
[data-testid="stSegmentedControl"] button {
  color:var(--marutai-navy) !important;
  background:#fff !important;
  border-color:var(--marutai-border) !important;
}
[data-testid="stSegmentedControl"] button[aria-pressed="true"] {
  background:var(--marutai-red-soft) !important;
  color:var(--marutai-red) !important;
  border-color:#e7aaa3 !important;
}

/* Uploader / camera */
[data-testid="stFileUploader"], [data-testid="stCameraInput"] { color:var(--marutai-navy) !important; }
[data-testid="stFileUploaderDropzone"] {
  background:#fff !important;
  border:1px dashed #c8bca8 !important;
  border-radius:16px !important;
}
[data-testid="stFileUploaderDropzone"] * { color:var(--marutai-navy) !important; }
[data-testid="stFileUploaderDropzoneInstructions"] > div { display:none !important; }
[data-testid="stFileUploaderDropzoneInstructions"]::before {
  content:"写真をここに追加";
  display:block;
  color:var(--marutai-navy);
  font-weight:800;
  margin-bottom:2px;
}
[data-testid="stFileUploaderDropzoneInstructions"]::after {
  content:"JPG・PNG・WEBP";
  display:block;
  color:var(--marutai-muted);
  font-size:.78rem;
}
[data-testid="stFileUploaderDropzone"] button { font-size:0 !important; }
[data-testid="stFileUploaderDropzone"] button::after {
  content:"写真を選ぶ";
  font-size:.9rem;
  color:var(--marutai-navy);
  font-weight:800;
}

/* Status boxes */
[data-testid="stAlert"] { border-radius:14px !important; }
[data-testid="stAlert"] p { color:var(--marutai-navy) !important; }

/* Brand */
.brand-fallback { display:flex; align-items:center; justify-content:center; gap:14px; margin:0 auto 10px; }
.brand-stamp {
  width:84px; height:84px; border:6px solid var(--marutai-red); border-radius:50%; color:var(--marutai-red);
  display:flex; align-items:center; justify-content:center; font-size:30px; font-weight:900; transform:rotate(-4deg);
  box-shadow:inset 0 0 0 3px #fff9ec;
}
.brand-title { color:var(--marutai-navy); font-weight:900; font-size:29px; line-height:1.02; letter-spacing:.02em; }
.brand-sub { color:var(--marutai-navy); font-weight:700; font-size:12px; margin-top:6px; }
.hero-question { color:var(--marutai-navy); text-align:center; font-size:1.18rem; font-weight:900; margin:.25rem 0 .75rem; }
.count-card {
  margin-top:.9rem; border:1px solid var(--marutai-border); border-radius:18px; padding:15px 18px; text-align:center;
  background:linear-gradient(135deg,#fff,#f7fbff); box-shadow:0 2px 10px rgba(79,55,22,.05);
}
.count-card span { display:block; color:var(--marutai-navy); font-weight:800; }
.count-card strong { display:block; color:var(--marutai-red); font-size:2.7rem; line-height:1.05; margin-top:4px; }
[data-testid="stMetric"] { background:#fff; border:1px solid var(--marutai-border); border-radius:14px; padding:9px; }

/* Facility cards */
.facility-card {
  border:0;
  border-radius:17px;
  padding:14px 15px 11px;
  margin:.4rem 0 .18rem;
  background:rgba(255,255,255,.94);
  box-shadow:none;
}
.facility-card-title { color:var(--marutai-navy); font-weight:900; font-size:1.2rem; line-height:1.25; margin-bottom:7px; }
.facility-card-meta { color:#385672; font-size:.9rem; font-weight:700; margin-bottom:7px; }
.facility-tags { display:flex; flex-wrap:wrap; gap:6px; margin:5px 0 4px; }
.facility-tag {
  display:inline-flex; align-items:center; min-height:28px; padding:3px 9px; border-radius:999px;
  border:1px solid #d6e0e8; background:#f7fbfd; color:var(--marutai-navy); font-size:.82rem; font-weight:700;
}
.facility-tag.yes { border-color:#b8d9e5; background:#eff9fc; }
.facility-tag.no { border-color:#e2ddd4; background:#fbfaf7; color:#687889; }
.facility-status { margin-top:7px; color:var(--marutai-navy); font-weight:900; font-size:.9rem; }
.facility-status.visited { color:var(--marutai-red); }
.facility-card + div[data-testid="stButton"] button { min-height:42px !important; }

/* Detail */
.detail-summary {
  background:#fff; border:1px solid var(--marutai-border); border-radius:16px; padding:12px 14px; margin:.2rem 0 .6rem;
  color:var(--marutai-navy);
}
.detail-summary strong { color:var(--marutai-navy); }

/* Bottom navigation */
.nav-wrap {
  position:fixed; left:0; right:0; bottom:0; z-index:9999;
  background:rgba(255,253,248,.98); border-top:1px solid var(--marutai-border);
  padding:6px max(10px, env(safe-area-inset-right)) calc(8px + env(safe-area-inset-bottom)) max(10px, env(safe-area-inset-left));
  backdrop-filter:blur(9px);
}
.nav-inner { max-width:740px; margin:auto; display:grid; grid-template-columns:repeat(4,1fr); gap:5px; }
.nav-item {
  position:relative; text-align:center; color:var(--marutai-navy) !important; text-decoration:none !important;
  font-weight:800; font-size:.79rem; padding:6px 2px 7px; border-radius:11px;
}
.nav-item.active { color:var(--marutai-red) !important; background:var(--marutai-red-soft); }
.nav-item.active::after {
  content:""; position:absolute; left:24%; right:24%; bottom:2px; height:3px; border-radius:3px; background:var(--marutai-red);
}
.nav-icon { display:block; font-size:1.35rem; line-height:1.05; margin-bottom:3px; }

.st-key-bottom_nav {
  position:fixed; left:0; right:0; bottom:0; z-index:9999;
  background:#fffdf8; border-top:1px solid var(--marutai-border);
  padding:8px 10px calc(10px + env(safe-area-inset-bottom));
}
.st-key-bottom_nav > div { max-width:740px; margin:auto; }
.st-key-bottom_nav [data-testid="stHorizontalBlock"] { flex-wrap:nowrap !important; gap:4px !important; }
.st-key-bottom_nav [data-testid="stColumn"] { min-width:0 !important; width:25% !important; flex:1 1 0 !important; }
.st-key-bottom_nav button { padding:4px !important; font-size:.75rem !important; min-height:46px; }
/* Map iframe */
[data-testid="stIFrame"] { border-radius:16px; overflow:hidden; }

@media (max-width: 640px) {
  .block-container {
    padding-left:.72rem !important;
    padding-right:.72rem !important;
    padding-top:calc(var(--marutai-header-height) + var(--marutai-top-gap) + env(safe-area-inset-top, 0px)) !important;
    padding-bottom:9.2rem !important;
  }
  h1 { font-size:1.72rem !important; line-height:1.16 !important; margin:.1rem 0 .45rem !important; }
  h2 { font-size:1.4rem !important; }
  h3 { font-size:1.12rem !important; }
  .brand-title { font-size:25px; }
  .brand-stamp { width:72px; height:72px; font-size:26px; }
  .hero-question { font-size:1.08rem; margin:.15rem 0 .6rem; }
  .stButton > button, .stLinkButton > a { min-height:46px; font-size:.95rem !important; }
  .facility-card { padding:12px 12px 10px; border-radius:15px; }
  .facility-card-title { font-size:1.1rem; }
  .facility-card-meta, .facility-status { font-size:.86rem; }
  .facility-tag { font-size:.78rem; padding:2px 8px; }
  [data-testid="stExpander"] details > div { padding-left:.6rem !important; padding-right:.6rem !important; }
  [data-testid="stVerticalBlock"] { gap:.55rem !important; }
}
</style>
"""

# ── 1. 設定・Supabase保存 ────────────────────────────────────
def setting(name: str) -> str:
    try:
        return str(st.secrets.get(name, os.getenv(name, ""))).strip()
    except FileNotFoundError:
        return os.getenv(name, "").strip()


def require_access() -> None:
    required = ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "APP_PASSWORD")
    missing = [name for name in required if not setting(name)]
    if missing:
        st.info("初期設定が必要です。README.mdに沿って設定してください。")
        st.code("未設定: " + ", ".join(missing))
        st.stop()
    # 家族共通の記録帳。service roleを使うため、表示前にアクセスを確認する。
    import hashlib
    token = hashlib.sha256(setting("APP_PASSWORD").encode()).hexdigest()
    if st.session_state.get("access_token") == token:
        return
    with st.form("login"):
        entered = st.text_input("合言葉", type="password")
        if st.form_submit_button("開く", width="stretch"):
            if hmac.compare_digest(entered.encode(), setting("APP_PASSWORD").encode()):
                st.session_state["access_token"] = token
                st.rerun()
            else:
                st.error("合言葉が違います。")
    st.stop()


# セッションごとにクライアントを持ち、利用者間で接続状態を共有しない。
def db():
    signature = (setting("SUPABASE_URL"), setting("SUPABASE_SERVICE_ROLE_KEY"))
    if st.session_state.get("db_signature") != signature:
        st.session_state["db_client"] = create_client(*signature)
        st.session_state["db_signature"] = signature
    return st.session_state["db_client"]


def fetch_all(table: str, columns: str = "*", *, active_only=False, order="id") -> list[dict[str, Any]]:
    rows, offset = [], 0
    # APIの既定件数で切れないよう、全ページを取得する。
    while True:
        query = db().table(table).select(columns).order(order)
        if active_only:
            query = query.eq("active", True)
        batch = query.range(offset, offset + 499).execute().data or []
        if not batch:
            return rows
        rows.extend(batch)
        offset += len(batch)


def list_facilities(active_only: bool = True) -> list[dict[str, Any]]:
    cache_key = "facilities_active" if active_only else "facilities_all"
    cache = st.session_state.setdefault("run_data", {})
    if cache_key not in cache:
        rows = fetch_all("facilities", active_only=active_only)
        cache[cache_key] = sorted(rows, key=lambda f: (f.get("ward", ""), f.get("name", "")))
    return cache[cache_key]


def get_facility(facility_id: str) -> dict[str, Any] | None:
    return next((f for f in list_facilities(False) if str(f["id"]) == str(facility_id)), None)


def list_visits() -> list[dict[str, Any]]:
    cache = st.session_state.setdefault("run_data", {})
    if "visits" not in cache:
        rows = fetch_all("visits", "*, facilities(*)")
        cache["visits"] = sorted(rows, key=lambda v: (v["visited_date"], v.get("created_at", "")), reverse=True)
    return cache["visits"]


def visits_for_facility(facility_id: str) -> list[dict[str, Any]]:
    return [v for v in list_visits() if str(v["facility_id"]) == str(facility_id)]


def visited_facility_ids() -> set[str]:
    return {str(v["facility_id"]) for v in list_visits()}


def photo_path(path: str | None):
    if not path:
        return None
    # Storageは非公開。短時間だけ有効な閲覧URLを発行する。
    result = db().storage.from_(BUCKET).create_signed_url(path, 3600)
    return result.get("signedURL") or result.get("signedUrl")


def create_visit(facility_id: str, visited_date: str, original_bytes: bytes, stamped_bytes: bytes) -> dict[str, Any]:
    visit_id = str(uuid4())
    original_path = f"original/{facility_id}/{visit_id}.jpg"
    stamped_path = f"stamped/{facility_id}/{visit_id}.jpg"
    row = dict(id=visit_id, facility_id=facility_id, visited_date=visited_date,
               original_photo_url=original_path, stamped_photo_url=stamped_path)
    bucket = db().storage.from_(BUCKET)
    uploaded = []
    try:
        for path, data in ((original_path, original_bytes), (stamped_path, stamped_bytes)):
            bucket.upload(path, data, file_options={"content-type": "image/jpeg", "upsert": "false"})
            uploaded.append(path)
        db().table("visits").insert(row).execute()
    except Exception:
        # 通信断でDBの応答だけ失われた場合は、保存済み写真を消さない。
        try:
            saved = db().table("visits").select("id").eq("id", visit_id).execute().data
        except Exception:
            LOGGER.exception("保存状態を確認できません: %s", visit_id)
            raise
        if not saved:
            if uploaded:
                try:
                    bucket.remove(uploaded)
                except Exception:
                    LOGGER.exception("未使用写真を削除できません: %s", visit_id)
            raise
    st.session_state["run_data"] = {}
    return row


# ── 公開施設一覧の検索・正規化（保存形式は既存facilitiesの11列） ──
FACILITY_LIST_URL = "https://jfsc.jp/data/sento/tokyo/"
FACILITY_CREDIT = "株式会社日本財務戦略センター（JFSC）『東京都の銭湯一覧』"
FACILITY_COLUMNS = ("id", "name", "category", "ward", "address", "latitude", "longitude",
                    "has_open_air_bath", "has_natural_hot_spring", "website_url", "active")


def public_json_or_text(url: str, *, params=None):
    import urllib.request
    import urllib.parse
    if params:
        url += "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={"User-Agent": "MarutaiStampRally/1.0 (personal facility map)"})
    with urllib.request.urlopen(request, timeout=18) as response:
        raw = response.read(8_000_001)
        if len(raw) > 8_000_000:
            raise ValueError("取得データが大きすぎます。")
        return raw.decode("utf-8-sig")


def normalized_name(value: str) -> str:
    import unicodedata
    import re
    value = unicodedata.normalize("NFKC", value)
    return re.sub(r"[\s・･()（）～~ー−‐―-]", "", value).lower()


def normalized_address(value: str) -> str:
    import re
    import unicodedata
    value = unicodedata.normalize("NFKC", value)
    digits = dict(zip("〇一二三四五六七八九", "0123456789"))
    def number(match):
        t = match.group()
        if "十" in t:
            a, b = t.split("十", 1)
            return str(int(digits.get(a, "1")) * 10 + int(digits.get(b, "0")))
        return "".join(digits[c] for c in t)
    value = re.sub(r"[〇一二三四五六七八九十]+(?=丁目|番|号)", number, value)
    value = re.sub(r"[−‐‑‒–—―ーｰ]", "-", value)
    value = re.sub(r"丁目|番地?|号", "-", value)
    return re.sub(r"\s+", "", value).rstrip("-")


def parse_public_facility_list(html: str) -> list[dict[str, Any]]:
    from html.parser import HTMLParser
    import re
    class TableParser(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.rows, self.row, self.cell = [], None, None
        def handle_starttag(self, tag, attrs):
            if tag == "tr":
                self.row = []
            elif tag == "td":
                self.cell = ""
        def handle_data(self, data):
            if self.cell is not None:
                self.cell += data
        def handle_endtag(self, tag):
            if tag == "td" and self.cell is not None:
                if self.row is not None:
                    self.row.append(self.cell.strip())
                self.cell = None
            elif tag == "tr" and self.row is not None:
                self.rows.append(self.row)
                self.row = None
    parser = TableParser()
    parser.feed(html)
    rows = {}
    for cells in parser.rows:
        if len(cells) < 2:
            continue
        name, address = cells[:2]
        match = re.match(r"東京都(" + "|".join(WARDS) + r")", address)
        if not match or not name:
            continue
        ward = match.group(1)
        key = "marutai-public:" + normalized_name(name) + ":" + normalized_address(address)
        fid = str(uuid5(NAMESPACE_URL, key))
        rows[fid] = dict(id=fid, name=name, category="sento", ward=ward, address=address,
                         latitude=None, longitude=None, has_open_air_bath=None,
                         has_natural_hot_spring=None, website_url="", active=True)
    if not rows:
        raise ValueError("取得元の施設一覧を読み取れませんでした。保存済みデータは変更していません。")
    return sorted(rows.values(), key=lambda row: (row["ward"], row["name"]))


def geocode_facility_address(address: str):
    import json
    import re
    # 街区番号まで一致した候補だけ採用し、町丁目の代表点は施設位置として使わない。
    normalized = normalized_address(address)
    if len(re.findall(r"\d+", normalized)) < 2:
        return None
    candidates = json.loads(public_json_or_text(
        "https://msearch.gsi.go.jp/address-search/AddressSearch", params={"q": address}))
    exact = []
    for feature in candidates if isinstance(candidates, list) else []:
        title = str(feature.get("properties", {}).get("title", ""))
        if normalized_address(title) != normalized:
            continue
        xy = feature.get("geometry", {}).get("coordinates", [])
        if len(xy) != 2:
            continue
        lon, lat = map(float, xy)
        if math.isfinite(lat) and math.isfinite(lon) and 35.50 <= lat <= 35.90 and 139.50 <= lon <= 139.98:
            exact.append((lat, lon))
    return exact[0] if len(set(exact)) == 1 else None


def validate_facility_rows(rows):
    import json
    ids = set()
    for row in rows:
        if set(row) != set(FACILITY_COLUMNS):
            raise ValueError("施設データの列が既存の保存形式と一致しません。")
        UUID(row["id"])
        if row["id"] in ids or not row["name"] or row["category"] not in CATEGORY_LABELS or row["ward"] not in WARDS:
            raise ValueError("施設の名称・種類・区・IDを確認できませんでした。")
        ids.add(row["id"])
        for key in ("has_open_air_bath", "has_natural_hot_spring"):
            if row[key] is not None and type(row[key]) is not bool:
                raise ValueError("設備情報の型が不正です。")
        if (row["latitude"] is None) != (row["longitude"] is None):
            raise ValueError("緯度経度が揃っていません。")
        if row["latitude"] is not None:
            if not (math.isfinite(row["latitude"]) and math.isfinite(row["longitude"]) and
                    35.50 <= row["latitude"] <= 35.90 and 139.50 <= row["longitude"] <= 139.98):
                raise ValueError("位置情報が東京23区周辺の範囲外です。")
    json.dumps(rows, allow_nan=False)
    return rows


def match_existing_facilities(rows, existing):
    # 名称・区・住所で既存IDを再利用し、訪問履歴との結びつきを維持する。
    by_address, by_name = {}, {}
    for old in existing:
        if str(old.get("name", "")).startswith("施設データ例"):
            continue
        addr_key = (old.get("ward"), normalized_address(old.get("address", "")))
        by_address.setdefault(addr_key, []).append(old)
        name_key = (old.get("ward"), normalized_name(old.get("name", "")))
        by_name.setdefault(name_key, []).append(old)
    result = []
    for incoming in rows:
        row = dict(incoming)
        candidates = by_name.get((row["ward"], normalized_name(row["name"])), [])
        old = candidates[0] if len(candidates) == 1 else None
        if old is None:
            candidates = by_address.get((row["ward"], normalized_address(row["address"])), [])
            old = candidates[0] if len(candidates) == 1 and (
                normalized_name(row["name"]) in normalized_name(candidates[0].get("name", "")) or
                normalized_name(candidates[0].get("name", "")) in normalized_name(row["name"])) else None
        if old:
            row["id"] = str(old["id"])
            # 取得元にない設備・公式URL・座標を、既知の値で上書きしない。
            same_address = normalized_address(row["address"]) == normalized_address(old.get("address", ""))
            for key in ("has_open_air_bath", "has_natural_hot_spring", "website_url"):
                if row[key] in (None, "") and old.get(key) not in (None, "") and same_address:
                    row[key] = old[key]
            if same_address and old.get("latitude") is not None and old.get("longitude") is not None:
                row["latitude"], row["longitude"] = old["latitude"], old["longitude"]
            row["category"] = old.get("category") or row["category"]
            row["active"] = old.get("active", True)
        result.append(row)
    return validate_facility_rows(result)


def save_searched_facilities(rows):
    # 取得・形式検証が完了するまでDBを更新しない。未取得施設を削除しない。
    validate_facility_rows(rows)
    for start in range(0, len(rows), 100):
        db().table("facilities").upsert(rows[start:start+100], on_conflict="id").execute()
    st.session_state["run_data"] = {}


def search_facility_list(*, update_positions=False):
    import json
    existing = list_facilities(False)
    try:
        rows = parse_public_facility_list(public_json_or_text(FACILITY_LIST_URL))
        source_note = "公開一覧から取得"
    except Exception:
        LOGGER.exception("公開施設一覧の取得失敗")
        if existing:
            raise RuntimeError("施設一覧を取得できませんでした。保存済みデータはそのまま表示します。")
        rows = [dict(row) for row in INITIAL_FACILITIES]
        source_note = "2026年10月25日に取得した公開一覧を使用（取得元への接続失敗）"
    # 検証済みの取得時点の座標を使い、初回の住所検索待ちを減らす。
    initial = {r["id"]: r for r in INITIAL_FACILITIES}
    for row in rows:
        old = initial.get(row["id"])
        if old:
            row["latitude"], row["longitude"] = old["latitude"], old["longitude"]
    rows = match_existing_facilities(rows, existing)
    save_searched_facilities(rows)
    for old in existing:
        if str(old.get("name", "")).startswith("施設データ例"):
            db().table("facilities").update({"active": False}).eq("id", old["id"]).execute()
    st.session_state["run_data"] = {}
    if update_positions:
        missing = [row for row in rows if row["latitude"] is None]
        bar = st.progress(0, text=f"住所を確認しています：0／{len(missing)}")
        failed = 0
        for i, row in enumerate(missing, 1):
            try:
                point = geocode_facility_address(row["address"])
                if point:
                    row["latitude"], row["longitude"] = point
                    db().table("facilities").update({"latitude": point[0], "longitude": point[1]}).eq("id", row["id"]).execute()
            except Exception:
                failed += 1
                LOGGER.exception("住所確認失敗: %s", row["id"])
            bar.progress(i / max(1, len(missing)), text=f"住所を確認しています：{i}／{len(missing)}")
            if failed >= 3:
                st.warning("住所検索への接続が不安定なため中断しました。取得済みの施設は保存しています。")
                break
        bar.empty()
        st.session_state["run_data"] = {}
    located = sum(row["latitude"] is not None for row in rows)
    return f"{len(rows)}施設を保存しました。地図表示：{located}施設／位置未確認：{len(rows)-located}施設。{source_note}。"


def ensure_initial_facilities():
    existing = list_facilities(False)
    if any(not str(f.get("name", "")).startswith("施設データ例") for f in existing) or st.session_state.get("initial_search_attempted"):
        return
    st.session_state["initial_search_attempted"] = True
    try:
        with st.spinner("東京23区の施設一覧を検索・保存しています…"):
            message = search_facility_list()
        st.session_state["facility_search_message"] = message
    except Exception:
        LOGGER.exception("初回施設検索失敗")
        st.warning("施設一覧を読み込めませんでした。「施設一覧を検索して更新」から再実行できます。")


def render_data_settings() -> None:
    with st.expander("施設一覧の検索・更新"):
        st.caption("東京23区の銭湯一覧を検索して保存します。住所が確認できた施設を地図に表示します。")
        if st.button("施設一覧を検索して更新", key="search_facility_list", width="stretch"):
            try:
                with st.spinner("施設一覧を取得しています…"):
                    st.session_state["facility_search_message"] = search_facility_list(update_positions=True)
            except Exception:
                LOGGER.exception("施設一覧更新失敗")
                st.error("一覧を更新できませんでした。既存の施設と訪問記録は保持しています。")
        if st.session_state.get("facility_search_message"):
            st.info(st.session_state["facility_search_message"])
        st.caption("設備情報がない場合は未登録と表示します。一般銭湯の一覧で、スーパー銭湯等の網羅は保証しません。")
        st.markdown(f"出典：[{FACILITY_CREDIT}]({FACILITY_LIST_URL})（CC BY 4.0）。23区で抽出・保存形式に変換。")
        st.caption("位置情報：国土地理院の住所検索。住所との完全一致を確認して採用。現地の入口位置とは差が生じる場合があります。")


def feature_text(label: str, value: bool | None) -> str:
    return f"{label} 未登録" if value is None else f"{label}{'あり' if value else 'なし'}"


def facility_label(f: dict) -> str:
    name, ward = str(f.get("name", "")), str(f.get("ward", ""))
    return name if not ward or ward in name else f"{name}（{ward}）"


# ── 2. 写真・共通表示 ──
Position = Literal["top_left", "top_right", "bottom_left", "bottom_right"]


def _date_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for candidate in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]:
        try:
            return ImageFont.truetype(candidate, size=size)
        except OSError:
            pass
    return ImageFont.load_default()


def add_visit_stamp(
    photo_bytes: bytes,
    visited_date: str,
    position: Position = "bottom_right",
) -> bytes:
    """Return JPEG bytes with the red 'たい' stamp and visit date overlaid.

    The original input bytes are never modified. The caller stores the original and
    returned versions separately.
    """
    base = Image.open(BytesIO(photo_bytes)).convert("RGB")
    stamp = Image.open(STAMP_PATH).convert("RGBA")

    width, height = base.size
    short_side = min(width, height)
    stamp_size = max(120, int(short_side * 0.26))
    stamp.thumbnail((stamp_size, stamp_size), Image.Resampling.LANCZOS)

    pad = max(16, int(short_side * 0.035))
    date_font = _date_font(max(18, int(stamp_size * 0.11)))
    date_text = visited_date.replace("-", ".")

    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    text_box = draw.textbbox((0, 0), date_text, font=date_font)
    text_w = text_box[2] - text_box[0]
    text_h = text_box[3] - text_box[1]
    block_w = max(stamp.width, text_w)
    block_h = stamp.height + text_h + max(5, int(stamp_size * 0.025))

    if position == "top_left":
        x, y = pad, pad
    elif position == "top_right":
        x, y = width - block_w - pad, pad
    elif position == "bottom_left":
        x, y = pad, height - block_h - pad
    else:
        x, y = width - block_w - pad, height - block_h - pad

    stamp_x = x + (block_w - stamp.width) // 2
    overlay.alpha_composite(stamp, dest=(stamp_x, y))

    text_x = x + (block_w - text_w) // 2
    text_y = y + stamp.height + max(5, int(stamp_size * 0.025))
    # Small cream keyline keeps the date readable on dark/light photos.
    draw.text(
        (text_x, text_y),
        date_text,
        font=date_font,
        fill=(198, 41, 35, 255),
        stroke_width=max(1, int(stamp_size * 0.01)),
        stroke_fill=(255, 249, 235, 235),
    )

    result = Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")
    out = BytesIO()
    result.save(out, format="JPEG", quality=92, optimize=True)
    return out.getvalue()

def render_logo(width: int = 310) -> None:
    logo = ASSET_DIR / "logo.png"
    if logo.exists():
        st.image(str(logo), width=width)
    else:
        st.markdown(
            "<div class='brand-fallback'><span class='brand-stamp'>たい</span>"
            "<div><div class='brand-title'>まるたい<br>スタンプラリー</div>"
            "<div class='brand-sub'>東京23区のおふろめぐり</div></div></div>",
            unsafe_allow_html=True,
        )

CATEGORY_LABELS = {
    "sento": "銭湯",
    "super_sento": "スーパー銭湯",
    "spa": "日帰り温浴施設",
    "other": "その他の温浴施設",
}


def _yn_tag(label: str, value: bool | None) -> str:
    css = "yes" if value else "no"
    text = feature_text(label, value)
    return f'<span class="facility-tag {css}">{escape(text)}</span>'


def render_facility_card(
    facility: dict[str, Any],
    visited: bool,
    on_detail: Callable[[str], None],
    key_prefix: str = "facility",
) -> None:
    name = escape(str(facility.get("name", "名称未設定")))
    ward = escape(str(facility.get("ward", "")))
    category = escape(CATEGORY_LABELS.get(facility.get("category"), "温浴施設"))
    state_text = "○たい　訪問済み" if visited else "未訪問"
    status_class = "facility-status visited" if visited else "facility-status"

    with st.container(border=True):
        st.markdown(
            f"""
            <div class="facility-card">
              <div class="facility-card-title">{name}</div>
              <div class="facility-card-meta">{ward}　｜　{category}</div>
              <div class="facility-tags">
                {_yn_tag("露天風呂", facility.get("has_open_air_bath"))}
                {_yn_tag("天然温泉", facility.get("has_natural_hot_spring"))}
              </div>
              <div class="{status_class}">{state_text}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("詳しく見る", key=f"{key_prefix}_{facility.get('id')}", width="stretch"):
            on_detail(str(facility.get("id")))

# ── 3. 地図 ──
TOKYO_CENTER = (35.6764, 139.7483)
TOKYO_23_BOUNDS = [[35.52, 139.55], [35.82, 139.93]]



def _valid_facilities(facilities: Iterable[dict[str, Any]]) -> list[tuple[dict[str, Any], float, float]]:
    valid: list[tuple[dict[str, Any], float, float]] = []
    for facility in facilities:
        lat = facility.get("latitude")
        lon = facility.get("longitude")
        if lat in (None, "") or lon in (None, ""):
            continue
        try:
            lat, lon = float(lat), float(lon)
            if math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180:
                valid.append((facility, lat, lon))
        except (TypeError, ValueError):
            continue
    return valid


def build_facility_map(
    facilities: Iterable[dict[str, Any]],
    visited_ids: set[str],
    zoom_start: int = 11,
    fit_23_wards: bool | None = None,
) -> folium.Map:
    facilities = list(facilities)
    valid = _valid_facilities(facilities)

    if fit_23_wards is None:
        fit_23_wards = zoom_start <= 12

    if fit_23_wards:
        center = TOKYO_CENTER
    elif len(valid) == 1:
        center = (valid[0][1], valid[0][2])
    elif valid:
        center = (
            sum(lat for _, lat, _ in valid) / len(valid),
            sum(lon for _, _, lon in valid) / len(valid),
        )
    else:
        center = TOKYO_CENTER

    m = folium.Map(
        location=center,
        zoom_start=zoom_start,
        tiles="OpenStreetMap",
        control_scale=True,
        prefer_canvas=True,
        min_zoom=9,
    )

    if fit_23_wards:
        m.fit_bounds(TOKYO_23_BOUNDS, padding=(8, 8))

    for facility, lat, lon in valid:
        fid = str(facility.get("id"))
        visited = fid in visited_ids

        if visited:
            marker_html = """
            <div style='width:42px;height:42px;border-radius:50%;background:#d9362b;color:white;
            border:4px solid #fff7e8;box-shadow:0 2px 8px #0003;display:flex;align-items:center;
            justify-content:center;font-weight:900;font-size:15px;font-family:sans-serif;'>たい</div>
            """
        else:
            marker_html = """
            <div style='width:36px;height:36px;border-radius:19px 19px 19px 4px;background:#173a5e;
            color:white;transform:rotate(-45deg);border:3px solid #fff7e8;box-shadow:0 2px 7px #0003;
            display:flex;align-items:center;justify-content:center;'>
              <span style='transform:rotate(45deg);font-size:19px;'>♨</span>
            </div>
            """

        name = escape(str(facility.get("name", "")))
        ward = escape(str(facility.get("ward", "")))
        category = escape(CATEGORY_LABELS.get(facility.get("category"), "温浴施設"))
        visit_text = "訪問済み" if visited else "未訪問"
        open_air = feature_text("露天風呂", facility.get("has_open_air_bath"))
        natural = feature_text("天然温泉", facility.get("has_natural_hot_spring"))

        detail_url = f"?view=facilities&facility_id={quote(fid, safe='')}"

        popup_html = f"""
        <div style="font-family:-apple-system,BlinkMacSystemFont,'Yu Gothic',sans-serif;color:#173a5e;min-width:190px;line-height:1.55;">
          <div style="font-size:16px;font-weight:800;margin-bottom:3px;">{name}</div>
          <div style="font-size:13px;">{ward}<br>施設種別：{category}</div>
          <div style="font-size:13px;font-weight:700;color:{'#d9362b' if visited else '#173a5e'};">{visit_text}</div>
          <div style="font-size:12px;margin-top:5px;">♨ {escape(open_air)}<br>♨ {escape(natural)}</div>
          <a href="{detail_url}" target="_top" style="display:block;margin-top:8px;padding:7px 10px;border-radius:9px;background:#d9362b;color:#fff;text-align:center;text-decoration:none;font-weight:800;font-size:13px;">詳しく見る</a>
        </div>
        """
        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(popup_html, max_width=280),
            tooltip=name,
            icon=folium.DivIcon(html=marker_html, icon_size=(42, 42), icon_anchor=(21, 36)),
        ).add_to(m)

    return m

# ── 4. 画面 ──
def render_home(go):
    render_logo()
    st.markdown("<div class='hero-question'>今日はどこのお風呂へ行く？</div>", unsafe_allow_html=True)

    if st.button("🗺️  地図から探す", key="home_map", type="primary", width="stretch"):
        go("map")
    if st.button("♨  露天風呂を探す", key="home_open_air", width="stretch"):
        go("map", open_air="1")
    if st.button("📖  スタンプ帳", key="home_stampbook", width="stretch"):
        go("stampbook")
    if st.button("📷  行ってきた！", key="home_visit", width="stretch"):
        go("visit")

    visits = list_visits()
    unique_facilities = {str(v.get("facility_id")) for v in visits}
    total = len(unique_facilities)
    st.markdown(
        f"<div class='count-card'><span>これまでに</span><strong>{total}湯！</strong></div>",
        unsafe_allow_html=True,
    )

    if visits:
        unique_by_facility = {}
        for v in visits:
            unique_by_facility.setdefault(str(v.get("facility_id")), v.get("facilities") or {})
        ward_counter = Counter(f.get("ward", "") for f in unique_by_facility.values())
        ward_counter.pop("", None)
        if ward_counter:
            st.markdown("#### 区ごとの記録")
            cols = st.columns(min(3, len(ward_counter)))
            for i, (ward, count) in enumerate(ward_counter.most_common(6)):
                cols[i % len(cols)].metric(ward, f"{count}湯")

        achieved = [n for n in (3, 5, 10, 20) if total >= n]
        if achieved:
            st.success(f"{max(achieved)}湯達成！")

WARDS = [
    "千代田区","中央区","港区","新宿区","文京区","台東区","墨田区","江東区","品川区","目黒区","大田区",
    "世田谷区","渋谷区","中野区","杉並区","豊島区","北区","荒川区","板橋区","練馬区","足立区","葛飾区","江戸川区",
]


def render_map(go):
    st.markdown("# 🗺️ 地図から探す")
    render_data_settings()
    facilities = list_facilities()
    visited = visited_facility_ids()

    if not facilities:
        st.warning("施設一覧をまだ取得できていません。上の「施設一覧を検索して更新」から再実行できます。")
        st_folium(build_facility_map([], visited), width=None, height=430, returned_objects=[])
        return

    default_open_air = st.query_params.get("open_air") == "1"
    with st.expander("絞り込み", expanded=True):
        category = st.multiselect(
            "施設種別",
            options=list(CATEGORY_LABELS.keys()),
            format_func=lambda x: CATEGORY_LABELS[x],
            placeholder="施設の種類を選ぶ",
        )
        open_air = st.checkbox("露天風呂あり", value=default_open_air)
        natural = st.checkbox("天然温泉あり")
        ward = st.selectbox("区を選ぶ", ["すべて"] + WARDS)
        visit_state = st.selectbox("訪問状態", ["すべて", "未訪問", "訪問済み"], index=0)

    filtered = []
    for f in facilities:
        fid = str(f.get("id"))
        if category and f.get("category") not in category:
            continue
        if open_air and not f.get("has_open_air_bath"):
            continue
        if natural and not f.get("has_natural_hot_spring"):
            continue
        if ward != "すべて" and f.get("ward") != ward:
            continue
        if visit_state == "訪問済み" and fid not in visited:
            continue
        if visit_state == "未訪問" and fid in visited:
            continue
        filtered.append(f)

    located = sum(f.get("latitude") is not None and f.get("longitude") is not None for f in filtered)
    st.caption(f"検索結果：{len(filtered)}施設 ｜ 地図：{located}施設 ｜ 位置未確認：{len(filtered)-located}施設")
    st_folium(
        build_facility_map(filtered, visited, zoom_start=11, fit_23_wards=True),
        width=None,
        height=455,
        returned_objects=[],
    )

    st.markdown("### 施設一覧")
    for f in filtered:
        render_facility_card(
            f,
            str(f.get("id")) in visited,
            lambda fid: go("facilities", facility_id=fid),
            "map",
        )
    if not filtered:
        st.info("条件に合う施設はありません。露天風呂・天然温泉が未登録の施設は、該当の絞り込みでは表示されません。")

def _detail(go, facility_id: str):
    f = get_facility(facility_id)
    if not f:
        st.error("施設情報が見つかりません。")
        if st.button("施設一覧へ戻る"):
            go("facilities")
        return

    visits = visits_for_facility(facility_id)
    name = escape(str(f.get("name", "")))
    ward = escape(str(f.get("ward", "")))
    category = escape(CATEGORY_LABELS.get(f.get("category"), "温浴施設"))
    address = escape(str(f.get("address", "")))
    status = "○たい　訪問済み" if visits else "未訪問"
    open_air = feature_text("露天風呂", f.get("has_open_air_bath"))
    natural = feature_text("天然温泉", f.get("has_natural_hot_spring"))

    st.markdown(f"# {name}")
    st.markdown(
        f"""
        <div class="detail-summary">
          <strong>{ward}</strong>　｜　{category}<br>
          {address}<br>
          <strong>{status}</strong><br>
          {escape(open_air)}　｜　{escape(natural)}
        </div>
        """,
        unsafe_allow_html=True,
    )

    if f.get("latitude") not in (None, "") and f.get("longitude") not in (None, ""):
        st_folium(
            build_facility_map([f], {facility_id} if visits else set(), zoom_start=15, fit_23_wards=False),
            width=None,
            height=300,
            returned_objects=[],
        )
    else:
        st.info("緯度・経度が未登録のため地図は表示できません。")

    if str(f.get("website_url") or "").startswith(("https://", "http://")):
        st.link_button("公式サイト", str(f.get("website_url")), width="stretch")

    if st.button("📷 この施設で『行ってきた！』", type="primary", width="stretch"):
        go("visit", facility_id=facility_id)

    st.markdown("### 訪問記録")
    if not visits:
        st.caption("まだ訪問記録はありません。")
    else:
        st.write(f"これまで **{len(visits)}回** 行ったよ")
        visits = sorted(visits, key=lambda v: str(v.get("visited_date", "")))
        for idx, visit in enumerate(visits, start=1):
            st.markdown(f"**{idx}回目**　{visit.get('visited_date','')}")
            url = photo_path(visit.get("stamped_photo_url"))
            if url:
                st.image(url, width="stretch")


def render_facilities(go):
    facility_id = st.query_params.get("facility_id")
    if facility_id:
        _detail(go, facility_id)
        return

    st.markdown("# お風呂を探す")
    render_data_settings()
    st.caption("施設名や区名から、行きたいお風呂を探せます。")
    facilities = list_facilities()
    visited = visited_facility_ids()
    query = st.text_input(
        "施設名・住所から検索",
        placeholder="例：品川、新生湯",
        label_visibility="collapsed",
    )
    if query:
        q = query.strip().lower()
        facilities = [
            f for f in facilities
            if q in str(f.get("name", "")).lower()
            or q in str(f.get("address", "")).lower()
            or q in str(f.get("ward", "")).lower()
        ]

    st.caption(f"{len(facilities)}施設")
    for f in facilities:
        render_facility_card(
            f,
            str(f.get("id")) in visited,
            lambda fid: go("facilities", facility_id=fid),
            "list",
        )
    if not facilities:
        st.info("条件に合う施設はありません。")

def _normalize_photo(raw: bytes) -> bytes:
    image = Image.open(BytesIO(raw))
    image = ImageOps.exif_transpose(image).convert("RGB")
    out = BytesIO()
    image.save(out, "JPEG", quality=94, optimize=True)
    return out.getvalue()


def render_visit(go):
    st.markdown("# 📷 行ってきた！")
    facilities = list_facilities()
    if not facilities:
        st.warning("施設一覧をまだ取得できていません。「その他」から施設一覧を検索して更新してください。")
        return

    preselected = st.query_params.get("facility_id", "")
    labels = {str(f.get("id")): facility_label(f) for f in facilities}
    ids = list(labels)
    initial = ids.index(preselected) if preselected in ids else 0

    st.markdown("### 1　訪問した施設を選ぶ")
    facility_id = st.selectbox(
        "施設",
        ids,
        index=initial,
        format_func=lambda x: labels[x],
        label_visibility="collapsed",
    )

    st.markdown("### 2　写真を撮影／選択")
    mode = st.radio("写真の追加方法", ["カメラで撮る", "写真を選ぶ"], horizontal=False)
    if mode == "カメラで撮る":
        st.caption("カメラの使用を許可してください。写真を選ぶ方法も使えます。")
    uploaded = (
        st.camera_input("銭湯・施設前で1枚", label_visibility="collapsed")
        if mode == "カメラで撮る"
        else st.file_uploader(
            "写真を選ぶ",
            type=["jpg", "jpeg", "png", "webp"],
            label_visibility="collapsed",
        )
    )

    st.markdown("### 3　訪問日")
    visited_date = st.date_input("訪問日", value=datetime.now(ZoneInfo("Asia/Tokyo")).date(), label_visibility="collapsed")

    st.markdown("### 4　スタンプを押す")
    if st.button("○たい　スタンプを押す！", type="primary", width="stretch"):
        if uploaded is None:
            st.warning("銭湯前の写真を1枚追加してね")
            return
        try:
            import hashlib
            fingerprint = hashlib.sha256(uploaded.getvalue() + facility_id.encode() + visited_date.isoformat().encode()).hexdigest()
            if fingerprint == st.session_state.get("last_saved_fingerprint"):
                st.info("この写真・施設・訪問日は保存済みです。")
                return
            original = _normalize_photo(uploaded.getvalue())
            stamped = add_visit_stamp(original, visited_date.isoformat(), position="bottom_right")
            create_visit(facility_id, visited_date.isoformat(), original, stamped)
            st.session_state["last_saved_fingerprint"] = fingerprint
            st.session_state["last_stamped_photo"] = stamped
            st.session_state["last_visit_facility"] = labels[facility_id]
            st.success("たい！またひとつ増えたよ！")
        except Exception as exc:
            st.error("訪問記録を保存できませんでした。写真を確認して、もう一度お試しください。")
            LOGGER.exception("訪問登録失敗")

    if st.session_state.get("last_stamped_photo"):
        st.image(
            st.session_state["last_stamped_photo"],
            caption=st.session_state.get("last_visit_facility", ""),
            width="stretch",
        )
        if st.button("スタンプ帳を見る", width="stretch"):
            go("stampbook")

def render_stampbook(go):
    st.markdown("# 📖 スタンプ帳")
    visits = list_visits()
    if not visits:
        st.info("まだスタンプがありません。『行ってきた！』から最初の1湯を記録できます。")
        return

    sort_mode = st.segmented_control(
        "並べ替え",
        ["新しい順", "古い順", "区ごと", "施設名順"],
        default="新しい順",
        selection_mode="single",
    )

    def name(v):
        return (v.get("facilities") or {}).get("name", "")

    def ward(v):
        return (v.get("facilities") or {}).get("ward", "")

    if sort_mode == "古い順":
        visits = sorted(visits, key=lambda v: str(v.get("visited_date", "")))
    elif sort_mode == "区ごと":
        visits = sorted(visits, key=lambda v: (ward(v), str(v.get("visited_date", ""))))
    elif sort_mode == "施設名順":
        visits = sorted(visits, key=lambda v: (name(v), str(v.get("visited_date", ""))))
    else:
        visits = sorted(visits, key=lambda v: str(v.get("visited_date", "")), reverse=True)

    # スマホ最優先のため1列表示。360px幅でも写真・文字・ボタンを潰さない。
    for visit in visits:
        f = visit.get("facilities") or {}
        with st.container(border=True):
            url = photo_path(visit.get("stamped_photo_url"))
            if url:
                st.image(url, width="stretch")
            st.markdown(f"### {f.get('name','施設名未取得')}")
            st.caption(f"○たい　{f.get('ward','')}　{visit.get('visited_date','')}")
            if st.button("詳しく見る", key=f"stamp_{visit.get('id')}", width="stretch"):
                go("facilities", facility_id=str(visit.get("facility_id")))

# ── 5. 画面遷移・起動 ──
def go(page: str, **params: str) -> None:
    st.session_state.pop("last_stamped_photo", None)
    st.session_state.pop("last_visit_facility", None)
    st.query_params.clear()
    st.query_params["view"] = page
    for key, value in params.items():
        if value not in (None, ""):
            st.query_params[key] = str(value)
    st.rerun()


def bottom_nav(active: str) -> None:
    # Streamlitボタンで移動し、認証・入力状態を保つ。
    with st.container(key="bottom_nav"):
        cols = st.columns(4)
        for col, (page, label) in zip(cols, [("home", "⌂ ホーム"), ("map", "🗺 地図"),
                                           ("stampbook", "▣ スタンプ帳"), ("facilities", "••• その他")]):
            with col:
                if st.button(label, key="nav_" + page, type="primary" if page == active else "secondary",
                             width="stretch"):
                    go(page)


def main() -> None:
    st.set_page_config(page_title="まるたいスタンプラリー", page_icon="♨️", layout="centered", initial_sidebar_state="collapsed")
    st.markdown(CSS, unsafe_allow_html=True)
    require_access()
    st.session_state["run_data"] = {}
    # 旧URLのpageにも互換対応。
    page = st.query_params.get("view", st.query_params.get("page", "home"))
    routes = {"home": render_home, "map": render_map, "facilities": render_facilities,
              "visit": render_visit, "stampbook": render_stampbook}
    try:
        ensure_initial_facilities()
        routes.get(page, render_home)(go)
    except Exception:
        LOGGER.exception("画面の読み込みに失敗: %s", page)
        st.error("データを読み込めませんでした。接続と初期設定を確認し、再読み込みしてください。")
        if st.button("再読み込み"):
            st.rerun()
    st.caption(f"施設一覧：[{FACILITY_CREDIT}]({FACILITY_LIST_URL}) / CC BY 4.0・23区を抽出。位置：国土地理院の住所検索。")
    bottom_nav(page if page in routes else "home")


if __name__ == "__main__":
    main()
