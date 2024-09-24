import unittest
from lxml import etree
import xml.etree.ElementTree as ET
from vespa.configuration.vt import *
from vespa.configuration.services import *


class TestVT(unittest.TestCase):
    def test_sanitize_tag_name(self):
        self.assertEqual(VT.sanitize_tag_name("content-node"), "content_node")
        self.assertEqual(VT.sanitize_tag_name("search-engine"), "search_engine")

    def test_restore_tag_name(self):
        self.assertEqual(VT.restore_tag_name("content_node"), "content-node")
        self.assertEqual(VT.restore_tag_name("search_engine"), "search-engine")

    def test_attrmap(self):
        self.assertEqual(attrmap("_max_memory"), "max-memory")
        self.assertEqual(attrmap("content_node"), "content-node")

    def test_valmap(self):
        self.assertEqual(valmap("test"), "test")
        self.assertEqual(valmap([1, 2, 3]), "1 2 3")

    def test_single_tag(self):
        content_tag = VT("content", (), {"attr": "value"})
        xml_output = to_xml(content_tag, indent=False)
        # Expecting the compact format without unnecessary newlines
        self.assertEqual(str(xml_output), '<content attr="value"></content>')

    def test_nested_tags(self):
        nested_tag = VT("content", (VT("document", ()),), {"attr": "value"})
        xml_output = to_xml(nested_tag, indent=False)
        # Expecting nested tags with proper newlines and indentation
        expected_output = '<content attr="value"><document></document></content>'
        self.assertEqual(str(xml_output), expected_output)

    def test_nested_tags_with_text(self):
        nested_tag = VT("content", (VT("document", ("text",)),), {"attr": "value"})
        xml_output = to_xml(nested_tag, indent=False)
        # Expecting nested tags with proper newlines and indentation
        parsed_output = ET.fromstring(str(xml_output))
        self.assertEqual(parsed_output.tag, "content")
        self.assertEqual(parsed_output.attrib, {"attr": "value"})
        self.assertEqual(parsed_output[0].tag, "document")
        self.assertEqual(parsed_output[0].text, "text")

    def test_void_tag(self):
        void_tag = VT("meta", (), void_=True)
        xml_output = to_xml(void_tag, indent=False)
        # Expecting a void tag with a newline at the end
        self.assertEqual(str(xml_output), "<meta />")

    def test_tag_with_attributes(self):
        tag_with_attr = VT(
            "content", (), {"max-size": "100", "compression-type": "gzip"}
        )
        xml_output = to_xml(tag_with_attr, indent=False)
        # Expecting the tag with attributes in compact format
        expected_output = '<content max-size="100" compression-type="gzip"></content>'
        self.assertEqual(str(xml_output), expected_output)

    def test_escape(self):
        unescaped_text = "<content>"
        self.assertEqual(vt_escape(unescaped_text), "&lt;content&gt;")

    def test_dynamic_tag_generation(self):
        for tag in services_tags:
            sanitized_name = VT.sanitize_tag_name(tag)
            tag_func = create_tag_function(tag, False)
            self.assertEqual(tag_func().__class__, VT)
            self.assertEqual(tag_func().tag, sanitized_name)

    def test_tag_addition(self):
        tag = VT("content", (), {"attr": "value"})
        new_tag = VT("document", ())
        tag = tag + new_tag
        self.assertEqual(len(tag.children), 1)
        self.assertEqual(tag.children[0].tag, "document")

    def test_repr(self):
        tag = VT("content", (VT("document", ()),), {"attr": "value"})
        self.assertEqual(repr(tag), "content((document((),{}),),{'attr': 'value'})")


class TestColbertServiceConfiguration(unittest.TestCase):
    def setUp(self):
        self.xml_file_path = "tests/testfiles/services/colbert/services.xml"
        self.xml_schema = """<?xml version="1.0" encoding="utf-8" ?>
    <services version="1.0" minimum-required-vespa-version="8.338.38">

        <!-- See https://docs.vespa.ai/en/reference/services-container.html -->
        <container id="default" version="1.0">

            <!-- See https://docs.vespa.ai/en/embedding.html#huggingface-embedder -->
            <component id="e5" type="hugging-face-embedder">
                <transformer-model url="https://huggingface.co/intfloat/e5-small-v2/resolve/main/model.onnx"/>
                <tokenizer-model url="https://huggingface.co/intfloat/e5-small-v2/raw/main/tokenizer.json"/>
                <!-- E5 prompt instructions -->
                <prepend>
                    <query>query:</query>
                    <document>passage:</document>
                </prepend>
            </component>

            <!-- See https://docs.vespa.ai/en/embedding.html#colbert-embedder -->
            <component id="colbert" type="colbert-embedder">
                <transformer-model url="https://huggingface.co/colbert-ir/colbertv2.0/resolve/main/model.onnx"/>
                <tokenizer-model url="https://huggingface.co/colbert-ir/colbertv2.0/raw/main/tokenizer.json"/>
            </component>

            <document-api/>
            <search/>
            <nodes count="1">
                <resources vcpu="4" memory="16Gb" disk="125Gb">
                    <gpu count="1" memory="16Gb"/>
                </resources>
            </nodes>
            
        </container>

        <!-- See https://docs.vespa.ai/en/reference/services-content.html -->
        <content id="text" version="1.0">
            <min-redundancy>2</min-redundancy>
            <documents>
                <document type="doc" mode="index" />
            </documents>
            <nodes count="2"/>
        </content>

    </services>
    """

    def test_valid_colbert_schema(self):
        to_validate = etree.parse(self.xml_file_path)
        # Validate against relaxng
        self.assertTrue(validate_services(to_validate))

    def test_valid_schema_from_string(self):
        to_validate = etree.fromstring(self.xml_schema.encode("utf-8"))
        self.assertTrue(validate_services(to_validate))

    def test_invalid_schema_from_string(self):
        invalid_xml = self.xml_schema.replace("document-api", "asdf")
        to_validate = etree.fromstring(invalid_xml.encode("utf-8"))
        self.assertFalse(validate_services(to_validate))

    def test_generate_colbert_services(self):
        self.maxDiff = None
        # Generated XML using dynamic tag functions
        generated_services = services(
            container(id="default", version="1.0")(
                component(id="e5", type="hugging-face-embedder")(
                    transformer_model(
                        url="https://huggingface.co/intfloat/e5-small-v2/resolve/main/model.onnx"
                    ),
                    tokenizer_model(
                        url="https://huggingface.co/intfloat/e5-small-v2/raw/main/tokenizer.json"
                    ),
                    prepend(query("query:"), document("passage:")),
                ),
                component(id="colbert", type="colbert-embedder")(
                    transformer_model(
                        url="https://huggingface.co/colbert-ir/colbertv2.0/resolve/main/model.onnx"
                    ),
                    tokenizer_model(
                        url="https://huggingface.co/colbert-ir/colbertv2.0/raw/main/tokenizer.json"
                    ),
                ),
                document_api(),
                search(),
                nodes(count="1")(
                    resources(vcpu="4", memory="16Gb", disk="125Gb")(
                        gpu(count="1", memory="16Gb")
                    )
                ),
            ),
            content(id="text", version="1.0")(
                min_redundancy("2"),
                documents(document(type="doc", mode="index")),
                nodes(count="2"),
            ),
            version="1.0",
            minimum_required_vespa_version="8.338.38",
        )
        generated_xml = generated_services.to_xml()
        # Validate against relaxng
        self.assertTrue(validate_services(etree.fromstring(str(generated_xml))))
        # Check all nodes and attributes being equal
        tree_original = ET.fromstring(self.xml_schema.encode("utf-8"))
        tree_generated = ET.fromstring(str(generated_xml))
        for original, generated in zip(tree_original.iter(), tree_generated.iter()):
            # print(f"Original: {original.tag}, {original.attrib}, {original.text}")
            # print(f"Generated: {generated.tag}, {generated.attrib}, {generated.text}")
            self.assertEqual(original.tag, generated.tag)
            self.assertEqual(original.attrib, generated.attrib)
            self.assertEqual(
                original.text.strip() if original.text else None,
                generated.text.strip() if generated.text else None,
            )


class TestBillionscaleServiceConfiguration(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self.xml_file_path = "tests/testfiles/services/billion-scale-image-search/src/main/application/services.xml"
        self.xml_schema = """<?xml version="1.0" encoding="utf-8" ?>
<services version='1.0' xmlns:deploy="vespa" xmlns:preprocess="properties">

  <container id='default' version='1.0'>
    <nodes count='1'/>
    <component id='ai.vespa.examples.Centroids' bundle='billion-scale-image-search'/>
    <component id='ai.vespa.examples.DimensionReducer' bundle='billion-scale-image-search'/>
    <component id="ai.vespa.examples.BPETokenizer" bundle='billion-scale-image-search'>
      <config name="ai.vespa.examples.bpe-tokenizer">
        <contextlength>77</contextlength>
        <vocabulary>files/bpe_simple_vocab_16e6.txt.gz</vocabulary>
      </config>
    </component>
    <model-evaluation>
      <onnx>
        <models>
          <model name="text_transformer">
            <intraop-threads>1</intraop-threads>
          </model>
          <model name="vespa_innerproduct_ranker">
            <intraop-threads>1</intraop-threads>
          </model>
        </models>
      </onnx>
    </model-evaluation>
    <search>
      <chain id='default' inherits='vespa'>
        <searcher id='ai.vespa.examples.searcher.DeDupingSearcher' bundle='billion-scale-image-search'/>
        <searcher id='ai.vespa.examples.searcher.RankingSearcher' bundle='billion-scale-image-search'/>
        <searcher id="ai.vespa.examples.searcher.CLIPEmbeddingSearcher" bundle="billion-scale-image-search"/>
        <searcher id='ai.vespa.examples.searcher.SPANNSearcher' bundle='billion-scale-image-search'/>
      </chain>
    </search>
    <document-api/>
    <document-processing>
      <chain id='neighbor-assigner' inherits='indexing'>
        <documentprocessor id='ai.vespa.examples.docproc.DimensionReductionDocProc'
                           bundle='billion-scale-image-search'/>
        <documentprocessor id='ai.vespa.examples.docproc.AssignCentroidsDocProc'
                           bundle='billion-scale-image-search'/>
      </chain>
    </document-processing>
  </container>

  <content id='graph' version='1.0'>
    <min-redundancy>1</min-redundancy>
    <documents>
      <document mode='index' type='centroid'/>
      <document-processing cluster='default' chain='neighbor-assigner'/>
    </documents>
    <nodes count='1'/>
    <engine>
      <proton>
        <tuning>
          <searchnode>
            <feeding>
              <concurrency>1.0</concurrency>
            </feeding>
          </searchnode>
        </tuning>
      </proton>
    </engine>
  </content>

  <content id='if' version='1.0'>
    <min-redundancy>1</min-redundancy>
    <documents>
      <document mode='index' type='image'/>
      <document-processing cluster='default' chain='neighbor-assigner'/>
    </documents>
    <nodes count='1'/>
    <engine>
      <proton>
        <tuning>
          <searchnode>
            <requestthreads>
              <persearch>2</persearch>
            </requestthreads>
            <feeding>
              <concurrency>1.0</concurrency>
            </feeding>
            <summary>
              <io>
                <read>directio</read>
              </io>
              <store>
                <cache>
                  <maxsize-percent>5</maxsize-percent>
                  <compression>
                    <type>lz4</type>
                  </compression>
                </cache>
                <logstore>
                  <chunk>
                    <maxsize>16384</maxsize>
                    <compression>
                      <type>zstd</type>
                      <level>3</level>
                    </compression>
                  </chunk>
                </logstore>
              </store>
            </summary>
          </searchnode>
        </tuning>
      </proton>
    </engine>
  </content>
</services>
"""

    def test_valid_billion_scale_config(self):
        to_validate = etree.parse(self.xml_file_path)
        # Validate against relaxng
        self.assertTrue(validate_services(to_validate))

    def test_config_from_string(self):
        to_validate = etree.fromstring(self.xml_schema.encode("utf-8"))
        self.assertTrue(validate_services(to_validate))

    def test_generate_billion_scale_services(self):
        # Generated XML using dynamic tag functions
        generated_services = services(
            container(id="default", version="1.0")(
                nodes(count="1"),
                component(
                    id="ai.vespa.examples.Centroids",
                    bundle="billion-scale-image-search",
                ),
                component(
                    id="ai.vespa.examples.DimensionReducer",
                    bundle="billion-scale-image-search",
                ),
                component(
                    id="ai.vespa.examples.BPETokenizer",
                    bundle="billion-scale-image-search",
                )(
                    config(name="ai.vespa.examples.bpe-tokenizer")(
                        vt(
                            "contextlength", "77"
                        ),  # using vt as this is not a predefined tag
                        vt(
                            "vocabulary", "files/bpe_simple_vocab_16e6.txt.gz"
                        ),  # using vt as this is not a predefined tag
                    ),
                ),
                model_evaluation(
                    onnx(
                        models(
                            model(name="text_transformer")(intraop_threads("1")),
                            model(name="vespa_innerproduct_ranker")(
                                intraop_threads("1")
                            ),
                        ),
                    ),
                ),
                search(
                    chain(id="default", inherits="vespa")(
                        searcher(
                            id="ai.vespa.examples.searcher.DeDupingSearcher",
                            bundle="billion-scale-image-search",
                        ),
                        searcher(
                            id="ai.vespa.examples.searcher.RankingSearcher",
                            bundle="billion-scale-image-search",
                        ),
                        searcher(
                            id="ai.vespa.examples.searcher.CLIPEmbeddingSearcher",
                            bundle="billion-scale-image-search",
                        ),
                        searcher(
                            id="ai.vespa.examples.searcher.SPANNSearcher",
                            bundle="billion-scale-image-search",
                        ),
                    ),
                ),
                document_api(),
                document_processing(
                    chain(id="neighbor-assigner", inherits="indexing")(
                        documentprocessor(
                            id="ai.vespa.examples.docproc.DimensionReductionDocProc",
                            bundle="billion-scale-image-search",
                        ),
                        documentprocessor(
                            id="ai.vespa.examples.docproc.AssignCentroidsDocProc",
                            bundle="billion-scale-image-search",
                        ),
                    ),
                ),
            ),
            content(id="graph", version="1.0")(
                min_redundancy("1"),
                documents(
                    document(mode="index", type="centroid"),
                    document_processing(cluster="default", chain="neighbor-assigner"),
                ),
                nodes(count="1"),
                engine(
                    proton(
                        tuning(
                            searchnode(
                                feeding(concurrency("1.0")),
                            ),
                        ),
                    ),
                ),
            ),
            content(id="if", version="1.0")(
                min_redundancy("1"),
                documents(
                    document(mode="index", type="image"),
                    document_processing(cluster="default", chain="neighbor-assigner"),
                ),
                nodes(count="1"),
                engine(
                    proton(
                        tuning(
                            searchnode(
                                requestthreads(persearch("2")),
                                feeding(concurrency("1.0")),
                                summary(
                                    io(read("directio")),
                                    store(
                                        cache(
                                            maxsize_percent("5"),
                                            compression(
                                                vt_type("lz4")
                                            ),  # Using vt_type as type is a reserved keyword
                                        ),
                                        logstore(
                                            chunk(
                                                maxsize("16384"),
                                                compression(
                                                    vt_type(
                                                        "zstd"
                                                    ),  # Using vt_type as type is a reserved keyword
                                                    level("3"),
                                                ),
                                            ),
                                        ),
                                    ),
                                ),
                            ),
                        ),
                    ),
                ),
            ),
            version="1.0",
        )
        # print(type(generated_services))
        generated_xml = generated_services.to_xml()
        # Validate against relaxng
        self.assertTrue(validate_services(etree.fromstring(str(generated_xml))))
        # Check all nodes and attributes being equal
        tree_original = ET.fromstring(self.xml_schema.encode("utf-8"))
        tree_generated = ET.fromstring(str(generated_xml))
        for original, generated in zip(tree_original.iter(), tree_generated.iter()):
            # print(f"Original: {original.tag}, {original.attrib}, {original.text}")
            # print(f"Generated: {generated.tag}, {generated.attrib}, {generated.text}")
            self.assertEqual(original.tag, generated.tag)
            self.assertEqual(original.attrib, generated.attrib)
            orig_text = original.text or ""
            gen_text = generated.text or ""
            self.assertEqual(orig_text.strip(), gen_text.strip())


if __name__ == "__main__":
    unittest.main()