from extractor.pdf_extractor import PdfExtractor


if __name__ == "__main__":
    extractor = PdfExtractor(
        "https://bagejj.oss-cn-heyuan.aliyuncs.com/templates/25AA0425%E6%A0%B7%E5%93%81%E9%A2%86%E5%8F%96_1e528404af9ed48963bc7339cf635ee0_1.pdf",
        tenant_id="1",
        user_id="1")
    extractor.extract()