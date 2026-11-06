#!/usr/bin/env python3
"""Pip: a small, consent-first people-search discovery assistant."""
from __future__ import annotations
import argparse, json, re, sys, time
from dataclasses import dataclass
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler

VERSION='0.1.0'
ENDPOINT='http://127.0.0.1:8888/search'
MAX_RESPONSE=2_000_000
@dataclass(frozen=True)
class Broker:
    id:str
    name:str
    domain:str
    optout:str
    note:str
BROKERS={b.id:b for b in [
    Broker('spokeo','Spokeo','spokeo.com','https://www.spokeo.com/optout','Requires a listing URL; follow the official opt-out flow.'),
    Broker('whitepages','Whitepages','whitepages.com','https://www.whitepages.com/privacy/consumer-rights','Uses a listing URL in the official consumer-rights flow.'),
]}
class PipError(Exception): pass
class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs): return None

def clean_identity(value:str,label:str,required:bool=False)->str:
    value=' '.join(value.split())
    if required and not value: raise PipError(f'{label} is required.')
    if len(value)>100: raise PipError(f'{label} must be 100 characters or fewer.')
    if any(c in value for c in '"\\') or any(ord(c)<32 for c in value):
        raise PipError(f'{label} cannot include quotes, backslashes, or control characters.')
    return value

def make_query(broker:Broker,name:str,place:str='')->str:
    name=clean_identity(name,'Name',True); place=clean_identity(place,'Location')
    # The location is unquoted to avoid over-constraining search results.
    return f'site:{broker.domain} "{name}"'+(f' {place}' if place else '')

def approved_result(url:str,broker:Broker)->bool:
    try:
        p=urlsplit(url);host=(p.hostname or '').lower().rstrip('.')
        return (p.scheme.lower()=='https' and bool(host) and not p.username and not p.password
                and (host==broker.domain or host.endswith('.'+broker.domain)) and p.port in (None,443))
    except (ValueError,AttributeError): return False

def display_text(s,limit=300):
    # Some search providers return HTML-marked snippets; show plain text only.
    s=re.sub(r'<[^>]*>',' ',str(s or ''));s=' '.join(s.split());return s[:limit]

def parse_results(payload,broker:Broker):
    if not isinstance(payload,dict) or not isinstance(payload.get('results'),list):
        raise PipError('The search service returned an invalid response.')
    matches=[];seen=set()
    for item in payload['results']:
        if not isinstance(item,dict): continue
        url=item.get('url','')
        if not isinstance(url,str) or not approved_result(url,broker) or url in seen:continue
        seen.add(url);matches.append({'broker':broker.name,'title':display_text(item.get('title'),160) or 'Untitled result','url':url,'snippet':display_text(item.get('content')),'optout':broker.optout})
        if len(matches)>=10:break
    return matches

def search(query:str,broker:Broker,opener=None):
    # POST avoids putting names in the local HTTP request URL. No redirects.
    body=urlencode({'q':query,'format':'json','categories':'general','pageno':'1'}).encode()
    req=Request(ENDPOINT,data=body,headers={'Content-Type':'application/x-www-form-urlencoded','Accept':'application/json','User-Agent':'Pryvate-Pip/0.1'},method='POST')
    opener=opener or build_opener(NoRedirect())
    try:
        with opener.open(req,timeout=25) as response:
            raw=response.read(MAX_RESPONSE+1)
            if len(raw)>MAX_RESPONSE:raise PipError('Search response exceeded the size limit.')
            result=json.loads(raw.decode('utf-8'))
    except HTTPError as e:
        if e.code==403:raise PipError('SearXNG refused JSON search. Enable JSON in searxng/settings.yml and restart it.') from None
        raise PipError(f'Search service returned HTTP {e.code}.') from None
    except (URLError,TimeoutError,OSError):raise PipError('Cannot reach local SearXNG at 127.0.0.1:8888. Start it first.') from None
    except (UnicodeError,json.JSONDecodeError):raise PipError('Search service did not return valid JSON.') from None
    return parse_results(result,broker)

from urllib.parse import unquote

def has_words(text, wanted):
    words = re.findall(r"\w+", text.casefold())
    target = re.findall(r"\w+", wanted.casefold())
    return bool(target) and any(words[i:i + len(target)] == target for i in range(len(words)))

def execute_scan(name,place,brokers,search_fn:Callable=search,delay=2):
    name=clean_identity(name,'Name',True);place=clean_identity(place,'Location')
    all_matches=[]; failures=[]
    for index,b in enumerate(brokers):
        if index and delay:time.sleep(delay)
        try:all_matches.extend(search_fn(make_query(b,name,place),b))
        except PipError as e:failures.append((b.name,str(e)))
    return all_matches,failures

def draft(name,email,broker):
    name=clean_identity(name,'Name',True);email=clean_identity(email,'Email')
    return (f'Subject: Request to delete my personal information\n\nHello {broker.name} privacy team,\n\n'
            'Please delete the personal information you hold about me and let me know how to opt out of its sale or sharing, where applicable. '
            'Please confirm when my request has been processed, or explain the next steps and any information you reasonably need to locate my record.\n\n'
            f'Name: {name}'+(f'\nEmail: {email}' if email else '')+f'\n\nThank you,\n{name}\n')

def choose_brokers(selection):return list(BROKERS.values()) if selection=='all' else [BROKERS[selection]]
def main():
    p=argparse.ArgumentParser(description='Pip: find possible public listings and review opt-out steps.')
    sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('brokers',help='List supported brokers and official opt-out pages')
    scan=sub.add_parser('scan',help='Search for your own possible listings (interactive)');scan.add_argument('--broker',choices=['all',*BROKERS],default='all')
    d=sub.add_parser('draft',help='Prepare a request for you to review and send');d.add_argument('--broker',choices=list(BROKERS),required=True)
    args=p.parse_args()
    if args.command=='brokers':
        for b in BROKERS.values():print(f'{b.name} ({b.id})\n  {b.optout}\n  {b.note}\n')
        return 0
    if args.command=='draft':
        b=BROKERS[args.broker];print(f'Official opt-out: {b.optout}\n{b.note}\nThis draft does not submit anything. The broker may require its form.\n')
        name=clean_identity(input('Your name: '),'Name',True);email=clean_identity(input('Email (optional): '),'Email');print('\n'+draft(name,email,b));return 0
    print('Pip only searches for your own information, or with the person\'s permission.\n'
          'Your search terms go to your local SearXNG instance and its configured search engines.\n'
          'SearXNG or those engines may keep logs; use only an instance you trust.\n'
          'Results are possible matches, not proof a listing is yours. No requests are sent.\n')
    if input('I understand and authorize this search [y/N]: ').strip().lower()!='y':print('No search performed.');return 0
    name=clean_identity(input('Name to search: '),'Name',True);place=clean_identity(input('City or state (optional): '),'Location')
    street=clean_identity(input("Street address for local filtering (optional): "),"Street address")
    brokers=choose_brokers(args.broker);print('\nSearching public search results. This can take a moment...\n')
    matches,failures=execute_scan(name,place,brokers)
    matches=[m for m in matches if has_words(m["title"], name) and (not street or has_words(" ".join((m["title"],m["snippet"],unquote(m["url"]))), street))]
    for b in brokers:
        items=[m for m in matches if m['broker']==b.name];print(f'=== {b.name} ===')
        if not items:
            if any(name == b.name for name, _ in failures): print('Search failed; no conclusion can be drawn.')
            else: print('No matching titles or addresses returned. This does not mean your data is absent.')
        for i,m in enumerate(items,1):
            print(f'{i}. {m["title"]}\n   {m["url"]}')
            if m['snippet']:print(f'   {m["snippet"]}')
        print(f'Official opt-out: {b.optout}\n{b.note}\n')
    if failures:
        print('Some searches failed:');[print(f'  {broker}: {error}') for broker,error in failures]
        return 2
    print('Review each result carefully. Do not submit identity documents unless you have verified the recipient and understand what is required.')
    return 0
if __name__=='__main__':
    try:sys.exit(main())
    except (PipError,KeyboardInterrupt,EOFError) as e:
        print('\nStopped.' if not isinstance(e,PipError) else f'Pip: {e}',file=sys.stderr);sys.exit(1)
