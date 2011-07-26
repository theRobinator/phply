import urllib
import urllib2
import json
import sys

RPC_HOST = 'www.rpc.vip.facebook.com'
RPC_PORT = 8083
RPC_AUTH = 'salted917urls'
RPC_TIMEOUT = 3

def hphp_rpc(function_name, parameters, host = RPC_HOST,
    port = RPC_PORT, auth = RPC_AUTH, timeout = RPC_TIMEOUT):
  """Execute PHP call via HPHP RPC service.
  See: https://www.intern.facebook.com/intern/wiki/index.php/HphpRpcGeneric

  parameters should be a tuple of the parameters to pass to the function
  to execute.
  """
  params = {
    "auth" : auth,
    "output": 2
  }
  url = 'http://%s:%d/%s?%s' % \
    (host, port, function_name, urllib.urlencode(params))
  for p in parameters:
    url += '&' + urllib.urlencode({"p": json.dumps(p)})
  http_res = urllib2.urlopen(url, timeout = timeout)
  body = http_res.read()
  r = json.loads(body)
  if http_res.getcode() != 200:
    raise RuntimeError('Non 200 return code: %d %s' %
            (http_res.getcode(), body))
  ret = {"output":r['output'], "return" : json.loads(r['return'])}
  return ret

class HphpCallable():
  """Helper used by HphpRpc.  Do not use"""
  def __init__(self, hphp_rpc, func):
    self.hphp_rpc = hphp_rpc
    self.func = func
  def __call__(self, *args):
    ret = hphp_rpc(self.func, args, self.hphp_rpc.host, self.hphp_rpc.port,
                   self.hphp_rpc.auth, self.hphp_rpc.timeout)
    sys.stdout.write(ret["output"])
    return ret["return"]

class HphpRpc():
  """ Allows easy execution of PHP functions via RPC using a simple syntax.
  See __main__ for examples """
  def __init__(self, host=RPC_HOST, port=RPC_PORT, auth=RPC_AUTH,
          timeout=RPC_TIMEOUT):
    self.host = host
    self.port = port
    self.auth = auth
    self.timeout = timeout
    self.base_function = ''

  def __getattr__(self, name):
    return HphpCallable(self, name)

if __name__ == '__main__':
  a = hphp_rpc('array_sum', ([0, 1, 2],))
  assert a['return'] == 3, "Cannot array_sum"

  a = hphp_rpc('print_r', ("hello",))
  assert a['output'] == "hello", "Cannot get stdout"

  R = HphpRpc()
  assert R.array_sum([0, 1, 2])['return'] == 3, "Cannot HPHP rpc array sum"
  assert R.print_r('hello')['output'] == 'hello', "Cannot HPHP rpc stdout"
