import json, os, sys, unittest
from io import BytesIO
sys.path.insert(0,os.path.dirname(os.path.dirname(__file__)))
import pipbot as p
class Resp(BytesIO):
    def __enter__(self):return self
    def __exit__(self,*a):self.close()
class FakeOpener:
    def __init__(self,obj):self.obj=obj;self.request=None
    def open(self,request,timeout):
        self.request=request
        return Resp(json.dumps(self.obj).encode())
class TestPip(unittest.TestCase):
    def setUp(self):self.b=p.BROKERS['spokeo']
    def test_query(self):self.assertEqual(p.make_query(self.b,' Jane  Doe ','Chicago IL'),'site:spokeo.com "Jane Doe" Chicago IL')
    def test_identity_validation(self):
        for x in ['"bad"','x\\y','']:
            with self.assertRaises(p.PipError):p.make_query(self.b,x)
    def test_allowlist(self):
        self.assertTrue(p.approved_result('https://www.spokeo.com/jane-doe',self.b))
        for u in ['http://spokeo.com/a','https://spokeo.com.attacker.test','https://spokeo.com@attacker.test','https://spokeo.com:444/a','javascript:alert(1)','https://attacker.test/spokeo.com']:
            self.assertFalse(p.approved_result(u,self.b),u)
    def test_parse_and_dedupe(self):
        data={'results':[{'title':'<b>Jane</b>','url':'https://www.spokeo.com/Jane','content':'<em>result</em>'},{'url':'https://www.spokeo.com/Jane'},{'url':'https://evil.example/spokeo.com'}]}
        r=p.parse_results(data,self.b);self.assertEqual(len(r),1);self.assertEqual(r[0]['title'],'Jane');self.assertEqual(r[0]['snippet'],'result')
    def test_search_posts_name_not_in_url(self):
        op=FakeOpener({'results':[{'url':'https://spokeo.com/test','title':'Result'}]})
        r=p.search('private name',self.b,opener=op);self.assertEqual(len(r),1);self.assertEqual(op.request.method,'POST');self.assertNotIn('private',op.request.full_url);self.assertIn(b'private+name',op.request.data)
    def test_bad_payload(self):
        with self.assertRaises(p.PipError):p.parse_results({'results':'bad'},self.b)
    def test_partial_failure(self):
        def fake(q,b):
            if b.id=='spokeo':raise p.PipError('failed')
            return [{'broker':b.name}]
        result,fail=p.execute_scan('Jane','',list(p.BROKERS.values()),fake,0);self.assertEqual(len(result),1);self.assertEqual(len(fail),1)
    def test_draft(self):
        out=p.draft('Jane Doe','',self.b);self.assertIn('Jane Doe',out);self.assertNotIn('Email:',out);self.assertNotIn('sent',out.lower())
if __name__=='__main__':unittest.main()
