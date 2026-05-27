import pandas as pd
from pandas import DataFrame

from pykrx.website.krx.krxio import KrxWebIo


class 전종목_시세_검색(KrxWebIo):
    @property
    def bld(self):
        return "dbms/MDC/STAT/standard/MDCSTAT14901"

    def fetch(
        self,
        locale: str = "ko_KR",
        trdDd: str = "20251120",
        share: str = "1",
        money: str = "1",
        csvxls_isNo: bool = False,
    ) -> DataFrame:
        """[16201] 전종목 시세
         - http://data.krx.co.kr/contents/MDC/MDI/mdiLoader/index.cmd?menuId=
           MDC0201060201

        Args:
            locale  (str, optional): 지역 선택 (default: "ko_KR")
            trdDd   (str, optional): 조회 일자 (default: "20251120")
            share   (str, optional): (default: "1")
            money   (str, optional): (default: "1")
            csvxls_isNo (str, optional): CSV/XLS 구분 (default: "false")
        Returns:
            DataFrame: 금 전종목 시세를 반환합니다.
            ISU_SRT_CD        ISU_CD MKT_ID       ISU_ABBRV TDD_CLSPRC FLUC_TP_CD  \
        0   04020000  KRD040200002    CMD     금 99.99_1Kg    193,890          2
        1   04020100  KRD040201000    CMD  미니금 99.99_100g    197,280          2

        CMPPREVDD_PRC FLUC_RT TDD_OPNPRC TDD_HGPRC TDD_LWPRC ACC_TRDVOL  \
        0          -460   -0.31    196,010   196,010   192,380    535,259
        1        -1,260    0.64    200,620   201,590   196,990      7,393

                ACC_TRDVAL
        0  104,044,785,230
        1    1,473,701,700
        """
        result = self.read(
            local=locale,
            trdDd=trdDd,
            share=share,
            money=money,
            csvxls_isNo=csvxls_isNo,
        )
        return DataFrame(result["output"])


class 개별종목_시세_추이(KrxWebIo):
    @property
    def bld(self):
        return "dbms/MDC/STAT/standard/MDCSTAT15001"

    def fetch(
        self, isuCd: str = "KRD040200002", strtDd: str = "", endDd: str = ""
    ) -> DataFrame:
        """[16202] 개별종목 시세 추이
         - http://data.krx.co.kr/contents/MDC/MDI/mdiLoader/index.cmd?menuId=
           MDC02021302
        Args:
            isuCd   (str): 종목 코드
            strtDd  (str): 조회 시작 일자 (YYYYMMDD)
            endDd   (str): 조회 종료 일자 (YYYYMMDD)
        Returns:
            DataFrame: 일별 금 시세 추이를 반환합니다.
        """
        result = self.read(
            isuCd=isuCd,
            strtDd=strtDd,
            endDd=endDd,
            share="1",
            money="1",
            csvxls_isNo=False,
        )
        return DataFrame(result["output"])


class 전종목_기본정보(KrxWebIo):
    @property
    def bld(self):
        return "dbms/MDC/STAT/standard/MDCSTAT15101"

    def fetch(self) -> DataFrame:
        """[16203] 전종목 기본정보
         - http://data.krx.co.kr/contents/MDC/MDI/mdiLoader/index.cmd?menuId=
           MDC0201060203

        Returns:
            DataFrame: 금 전종목 기본정보를 반환합니다.
        """
        result = self.read()
        return DataFrame(result["output"])


class 개별종목_종합정보(KrxWebIo):
    @property
    def bld(self):
        return "dbms/MDC/STAT/standard/MDCSTAT15202"

    def fetch(
        self, ddTp: str = "1D", locale: str = "ko_KR", isuCd: str = "KRD040200002"
    ) -> DataFrame:
        """[16204] 개별종목 종합정보
         - http://data.krx.co.kr/contents/MDC/MDI/mdiLoader/index.cmd?menuId=
           MDC0201060204
        Args:
            isuCd   (str): 종목 코드
            ddTp    (str): 기간 구분 (1D: 일간, 1W: 주간, 1M: 월간, 3M: 분기, 6M: 반기, 1Y: 연간)
            locale  (str): 지역 선택
            isuCd   (str): 종목 코드
            csvxls_isNo (str, optional): CSV/XLS 구분 (default: "false")
        Returns:
            DataFrame: 개별종목 종합정보를 반환합니다.
        """
        result = self.read(
            ddTp=ddTp,
            locale=locale,
            isuCd=isuCd,
            csvxls_isNo=False,
        )
        return DataFrame(result["output"])


class 일자별시세(KrxWebIo):
    @property
    def bld(self):
        return "dbms/MDC/STAT/standard/MDCSTAT15203"

    def fetch(self, locale: str = "ko_KR", isuCd: str = "KRD040200002") -> DataFrame:
        """
         - http://data.krx.co.kr/contents/MDC/MDI/mdiLoader/index.cmd?menuId=
           MDC0201060204
        Args:
            isuCd   (str): 종목 코드
            locale  (str): 지역 선택
            isuCd   (str): 종목 코드
            csvxls_isNo (str, optional): CSV/XLS 구분 (default: "false")
        Returns:
            DataFrame: 개별종목 종합정보를 반환합니다.
        """

        result = self.read(
            locale=locale,
            isuCd=isuCd,
            csvxls_isNo=False,
        )
        return DataFrame(result["output"])


class 투자자별_거래실적(KrxWebIo):
    @property
    def bld(self):
        return "dbms/MDC/STAT/standard/MDCSTAT15301"

    def fetch(
        self,
        locale: str = "ko_KR",
        inqTpCd: str = "1",
        trdVolVal: str = "2",
        bidAskNet: str = "3",
        strtDd: str = "20251117",
        endDd: str = "20251124",
        share: str = "1",
        money: str = "1",
        csvxls_isNo: str = "false",
    ) -> DataFrame:
        """[16205] 투자자별 거래실적
         - http://data.krx.co.kr/contents/MDC/MDI/mdiLoader/index.cmd?menuId=
           MDC0201060205
        Args:
            locale  (str, optional): 지역 선택 (default: "ko_KR")
            inqTpCd (str, optional): 조회 구분 (default: "1")
            trdVolVal (str, optional): 거래량/거래대금 구분 (default: "2")
            bidAskNet (str, optional): 매수/매도/순매수 구분 (default: "3")
            strtDd  (str, optional): 조회 시작 일자 (default: "20251117")
            endDd   (str, optional): 조회 종료 일자 (default: "20251124")
            share   (str, optional): (default: "1")
            money   (str, optional): (default: "1")
            csvxls_isNo (str, optional): CSV/XLS 구분 (default: "false")
        Returns:
            DataFrame: 투자자별 거래실적을 반환합니다.
        """
        result = self.read(
            locale=locale,
            inqTpCd=inqTpCd,
            trdVolVal=trdVolVal,
            bidAskNet=bidAskNet,
            strtDd=strtDd,
            endDd=endDd,
            share=share,
            money=money,
            csvxls_isNo=csvxls_isNo,
        )

        return DataFrame(result["output"])


class 협의대량거래실적_추이(KrxWebIo):
    @property
    def bld(self):
        return "dbms/MDC/STAT/standard/MDCSTAT15401"

    # bld=dbms/MDC/STAT/standard/MDCSTAT15401&locale=ko_KR&strtDd=20251117&endDd=20251124&share=1&csvxls_isNo=false
    def fetch(
        self,
        locale: str = "ko_KR",
        strtDd: str = "20251117",
        endDd: str = "20251124",
        share: str = "1",
        csvxls_isNo: str = "false",
    ) -> DataFrame:
        """[16206] 협의대량거래실적 추이
         - http://data.krx.co.kr/contents/MDC/MDI/mdiLoader/index.cmd?menuId=
           MDC0201060206
        Args:
            locale  (str, optional): 지역 선택 (default: "ko_KR")
            strtDd  (str, optional): 조회 시작 일자 (default: "20251117")
            endDd   (str, optional): 조회 종료 일자 (default: "20251124")
            share   (str, optional): (default: "1")
            csvxls_isNo (str, optional): CSV/XLS 구분 (default: "false")
        Returns:
            DataFrame: 협의대량거래실적 추이를 반환합니다.
        """
        result = self.read(
            locale=locale,
            strtDd=strtDd,
            endDd=endDd,
            share=share,
            csvxls_isNo=csvxls_isNo,
        )
        return DataFrame(result["output"])


class 국제금시세_동향(KrxWebIo):
    @property
    def bld(self):
        return "dbms/MDC/STAT/standard/MDCSTAT15401"

    def fetch(
        self,
        locale: str = "ko_KR",
        strtDd: str = "20251117",
        endDd: str = "20251124",
        share: str = "1",
        csvxls_isNo: str = "false",
    ) -> DataFrame:
        """[16207] 국제금시세 동향
         - http://data.krx.co.kr/contents/MDC/MDI/mdiLoader/index.cmd?menuId=
           MDC0201060207

        Returns:
            DataFrame: 국제금시세 동향을 반환합니다.
        """
        result = self.read(
            locale=locale,
            strtDd=strtDd,
            endDd=endDd,
            share=share,
            csvxls_isNo=csvxls_isNo,
        )
        return DataFrame(result["output"])


if __name__ == "__main__":
    pd.set_option("display.width", None)
    # 금 종목 확인
    print(전종목_시세_검색().fetch(trdDd="20251125").head())

    # isuCd: KRD040200002 금현물
    print(
        개별종목_시세_추이().fetch(
            isuCd="KRD040200002", strtDd="20251107", endDd="20251125"
        )
    )
    print(
        개별종목_종합정보()
        .fetch(ddTp="1D", isuCd="KRD040200002", locale="ko_KR")
        .head()
    )  # 일단위 조회
    print(일자별시세().fetch(locale="ko_KR", isuCd="KRD040200002").head())
    print(투자자별_거래실적().fetch(strtDd="20251001", endDd="20251125"))  # 기관 투자
    print(
        협의대량거래실적_추이().fetch(strtDd="20251001", endDd="20251125")
    )  # 협의대량거래실적 추이
    print(
        국제금시세_동향().fetch(strtDd="20251001", endDd="20251125")
    )  # 국제금시세 동향
