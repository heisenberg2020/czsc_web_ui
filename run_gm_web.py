# coding: utf-8
import json
import os
import pandas as pd
from tornado.ioloop import IOLoop
from tornado.httpserver import HTTPServer
from tornado.options import define, parse_command_line, options
from tornado.web import RequestHandler, Application
from tornado.web import StaticFileHandler
from datetime import datetime, timedelta
from czsc import KlineAnalyze
from gm.api import *
from utils.logger import Logger

log = Logger('all.log',level='debug').logger





#from conf import gm_token

# 在这里设置你的掘金 token，要在本地启动掘金终端，才能正常获取数据
# set_token("set your gm token")
set_token("03210e0e39013a46836b3afb9d25b57b871df5a2")

#logger = Logger(__name__).get_log()

def get_gm_kline(symbol, end_date, freq='D', k_count=3000):
    """从掘金获取历史K线数据"""

    if "-" not in end_date and isinstance(end_date, str):
        end_date = datetime.strptime(end_date, "%Y%m%d")
    freq_convert = {"60s": "1min", "300s": "5min", "1800s": "30min", "3600s": "60min", "1d": "D"}
    log.debug(freq_convert)
    freq_convert = {v: k for k, v in freq_convert.items()} #{'1min': '60s', '5min': '300s', '30min': '1800s', '60min': '3600s', 'D': '1d'}
    log.debug(freq_convert)
    if freq[-1] in ['n', 'D']:
        freq = freq_convert[freq]
        if freq.endswith('min'):
            end_date += timedelta(days=1)
    
    df = history_n(symbol=symbol, frequency=freq, end_time=end_date,
                   fields='symbol,eob,open,close,high,low,volume',
                   count=k_count, df=True)
    
    df['dt'] = df['eob']
    df['vol'] = df['volume']

    df = df[['symbol', 'dt', 'open', 'close', 'high', 'low', 'vol']] #调整列的顺序
    
    df.sort_values('dt', inplace=True, ascending=True)
    df['dt'] = df.dt.apply(lambda x: x.strftime(r"%Y-%m-%d %H:%M:%S"))
    df.reset_index(drop=True, inplace=True)
    for col in ['open', 'close', 'high', 'low']:
        df[col] = df[col].apply(round, args=(2,))  

    log.debug(df)  
    return df


# 端口固定为 8005，不可以调整
define('port', type=int, default=8005, help='服务器端口')
current_path = os.path.dirname(__file__)


class BaseHandler(RequestHandler):
    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", "*")  # 这个地方可以写域名
        self.set_header("Access-Control-Allow-Headers", "x-requested-with")
        self.set_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')

    def post(self):
        self.write('some post')

    def get(self):
        self.write('some get')

    def options(self):
        self.set_status(204)
        self.finish()


class BasicHandler(BaseHandler):
    """股票基本信息"""
    def get(self):
        ts_code = self.get_argument('ts_code')
        results = {"msg": "success", "basic": None}
        self.write(json.dumps(results, ensure_ascii=False))


class KlineHandler(BaseHandler):
    """K 线"""
    def get(self):
        ts_code = self.get_argument('ts_code')
        freq = self.get_argument('freq')
        trade_date = self.get_argument('trade_date')
        if trade_date == 'null':
            trade_date = datetime.now().date().__str__().replace("-", "")
        log.debug(ts_code)
        log.debug(freq)
        log.debug(trade_date)
        kline = get_gm_kline(symbol=ts_code, end_date=trade_date, freq=freq, k_count=1440)
        ka = KlineAnalyze(kline)
        kline = pd.DataFrame(ka.kline)
        kline = kline.fillna("")
        columns = ["dt", "open", "close", "low", "high", "vol", 'fx_mark', 'fx', 'bi', 'xd']

        self.finish({'kdata': kline[columns].values.tolist()})


if __name__ == '__main__':

    log.debug('start')

    pd.set_option('display.max_columns', None)    # 显示所有列
    pd.set_option('display.max_rows', None)      # 显示所有行

    parse_command_line()
    app = Application([
            ('/kline', KlineHandler),
            ('/basic', BasicHandler),
            (r'^/(.*?)$', StaticFileHandler, {"path": os.path.join(current_path, "web"),
                                              "default_filename": "index.html"}),
        ],
        static_path=os.path.join(current_path, "web"),
        dubug=True
    )
    http_server = HTTPServer(app)
    http_server.listen(options.port)
    IOLoop.current().start()

# 交易所代码如下：
# 上交所	SHSE
# 深交所	SZSE
# 中金所	CFFEX
# 上期所	SHFE
# 大商所	DCE
# 郑商所	CZCE
# 上海国际能源交易中心	INE

# 掘金数据文档：https://www.myquant.cn/docs/data/98?

# http://localhost:8005/?ts_code=SHSE.000001&asset=I&trade_date=20200613&freqs=D,30min,5min,1min
