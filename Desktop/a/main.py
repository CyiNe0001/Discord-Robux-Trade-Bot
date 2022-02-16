import discord
from discord import HTTPException
from discord.ext import commands
from discord.ext.commands import errors
from discord.utils import get
import re
from types import SimpleNamespace
import json
import os
import requests
import random
import http

cur_price = 0 #거래 가격

bot = commands.Bot(command_prefix=".")


try:
    
    from os import getenv

    token = getenv('Token')
    if not token:
        raise RuntimeError('토큰 없음')
except:
    token = "여기에 토큰 입력"



@bot.event
async def on_ready():
    rob = await parse_server()
    await bot.change_presence(activity=discord.Game(name=f"{str(rob)} Robux"))
    print("============================================")
    print(f"로그인 정보 : {bot.user.name}({bot.user.id})")
    print("개발자 Kon_UU")
    print("환영합니다.")
    print("============================================")


@bot.command()
async def 쿠키등록(ctx, cookie):
    await 계좌개설(ctx.author)
    a = await cookie_check(ctx, cookie)
    if a == 4:
        await ctx.send("[!] 쿠키 조회 중 오류가 발생 하였습니다.")
    else:
        await ctx.send("쿠키 등록 완료 .정보 로 확인하세요.")

@bot.command()
async def 정보(ctx):
    rob = await parse_server()
    await bot.change_presence(activity=discord.Game(name=f"{str(rob)} Robux"))
    await 계좌개설(ctx.author)

    try:

        with open(f"./userdata/{ctx.author.id}.json", 'r', encoding='utf-8') as boo:
            userdata = json.load(boo)
            username = userdata["username"]
            robux = userdata["robux"]

            em = discord.Embed(title = "현재 등록된 계정 정보",color=0x004DF7)
            em.add_field(name = "닉네임",value = f"{username}")
            em.add_field(name = "로벅스",value = f"⏣ {robux}")
            await ctx.send(embed = em)

    except Exception as err:
        await ctx.send(f"[!] 먼저 쿠키를 등록 하세요 {err}")

@bot.command()
async def 구매(ctx, gmp, amt):
    await 계좌개설(ctx.author)
    bank_data = await get_bank_data()
    amt = int(amt)

    if bank_data["wallet"] >= amt / 1000 * cur_price:
        print("거래 진행중..")
    else:
        ctx.send("[!] 잔액 부족")
        return

    acc_list = await parse_accounts(amt)
    if not bool(acc_list):
        await ctx.send(f"[!] 재고가 부족 합니다.")

    
    chosen_acc = random.choice(acc_list)
    chosen_uid = chosen_acc[:-5]
    print(chosen_uid)
    cookie = await get_cookie(chosen_acc)

    a = await cookie_check(ctx, cookie)

    xsrf = await get_xsrf(chosen_acc)

    if a == 4:
        await ctx.send("[!] 판매자 쿠키 조회 중 오류가 발생 하였습니다.")
        return

    detail_res = requests.get(f"https://www.roblox.com/game-pass/{gmp}")
    text = detail_res.text

    productId = int(re.search("data-product-id=\"(\d+)\"", text).group(1))
    expectedPrice = int(re.search("data-expected-price=\"(\d+)\"", text).group(1))
    expectedSellerId = int(re.search("data-expected-seller-id=\"(\d+)\"", text).group(1))

    if not int(amt) == expectedPrice:
        await ctx.send(f"[!] 잘못된 게임패스 가격")
        return

    headers = {
        "cookie": f".ROBLOSECURITY={cookie}",
        "x-csrf-token": xsrf
    }

    payload = {
        "expectedSellerId": expectedSellerId,
        "expectedCurrency": 1,
        "expectedPrice": expectedPrice
    }

    buyres = requests.post(f"https://economy.roblox.com/v1/purchases/products/{productId}", headers = headers, data = payload)
    try:
        if buyres.json()['title'] == 'Item Owned':
            await ctx.send("[!] 게임패스 구매중 오류, 이미 사용한 게임패스는 사용 X")
    except:
        None
    if buyres.json()['purchased'] == True:
        await ctx.send("구매 완료 !")
        bank_data[str(ctx.author.id)]["wallet"] -= amt / 1000 * cur_price
        bank_data[str(chosen_uid)]["wallet"] += amt / 950 * cur_price
        bank_data[str(chosen_uid)]["amount"] += amt / 950 * cur_price
        with open("userdata.json", "w") as f:
            json.dump(bank_data, f)

    print(buyres.json())


async def parse_accounts(rbx):
    path_to_json = './userdata/'
    acc_list = []

    for file_name in [file for file in os.listdir(path_to_json) if file.endswith('.json')]:
      with open(path_to_json + file_name) as json_file:
        data = json.load(json_file)
        if int(rbx) <= data["robux"]:
            acc_list.append(file_name)

    return acc_list

async def cookie_check(ctx, cookie):
    try:

        #Get Account Data
        conn = http.client.HTTPSConnection("www.roblox.com")
        conn.request("GET", "/mobileapi/userinfo", headers={"Cookie": f".ROBLOSECURITY={cookie}"})
        resp = conn.getresponse()
        data = resp.read()
        x = json.loads(data, object_hook=lambda d: SimpleNamespace(**d))

        #Get XSRF Token for Purchases
        conn = http.client.HTTPSConnection("auth.roblox.com")
        conn.request("POST", "/v2/login", headers={"Cookie": f".ROBLOSECURITY={cookie}"})
        resp = conn.getresponse()
        new_xsrf = resp.getheader("X-CSRF-TOKEN")
        data = resp.read()

    except Exception as err:

        return 4


    first_data = {
        "cookie": str(cookie),
        "username": str(x.UserName),
        "robux": int(x.RobuxBalance),
        "xsrf": str(new_xsrf)
    }
    with open(f"./userdata/{ctx.author.id}.json", 'w') as outfile:
        json.dump(first_data, outfile, indent=4)


async def get_xsrf(uid):
    with open(f"./userdata/{uid}", 'r', encoding='utf-8') as boo:
        userdata = json.load(boo)
        new_xsrf = userdata["xsrf"]

        return new_xsrf

async def get_cookie(uid):
    with open(f"./userdata/{uid}", 'r', encoding='utf-8') as boo:
        userdata = json.load(boo)
        return userdata["cookie"]

async def 계좌개설(user):
    users = await get_bank_data()

    if str(user.id) in users:

            return True
    else:
        users[str(user.id)] = {"wallet" : 0, "amount" : 0}

    with open("userdata.json", "w") as f:
        json.dump(users, f)
        
    return True

async def get_bank_data():
    with open("userdata.json", "r") as f:
        users = json.load(f)

    return users

async def parse_server():
    path_to_json = './userdata/'
    parsed_robux = 0

    for file_name in [file for file in os.listdir(path_to_json) if file.endswith('.json')]:
      with open(path_to_json + file_name) as json_file:
        data = json.load(json_file)
        parsed_robux += data["robux"]

    return parsed_robux

bot.run(token)