from ioscreen.asyn import create_hpa1_device, create_hpd1_device
from ioscreen.coremedia.serialize import SerializeStringKeyDict, new_dictionary_from_bytes, DictConst, \
    new_string_dict_from_bytes


def test_BooleanSerialization():
    with open('./fixtures/bulvalue.bin', "rb") as f:
        data = f.read()
    serializedDict = SerializeStringKeyDict({'Valeria': True})
    assert data == serializedDict.to_bytes()


def test_FullSerialization():
    with open('./fixtures/serialize_dict.bin', "rb") as f:
        data = f.read()
    serializedBytes = SerializeStringKeyDict(create_hpa1_device())
    assert data == serializedBytes.to_bytes()

    with open('./fixtures/dict.bin', "rb") as f:
        data = f.read()
    serializedBytes = SerializeStringKeyDict(create_hpd1_device())
    assert data == serializedBytes.to_bytes()


def test_IntDict():
    with open('./fixtures/intdict.bin', "rb") as f:
        data = f.read()

    mydict = new_dictionary_from_bytes(data, DictConst.DictionaryMagic)
    assert 2 == len(mydict)
    print(mydict)


def test_BooleanEntry():
    with open('./fixtures/bulvalue.bin', "rb") as f:
        data = f.read()
    mydict = new_string_dict_from_bytes(data)
    assert 1 == len(mydict)
    print(mydict)


def test_SimpleDict():
    with open('./fixtures/dict.bin', "rb") as f:
        data = f.read()

    mydict = new_string_dict_from_bytes(data)
    assert 3 == len(mydict)
    assert 1920.0 == mydict.get('DisplaySize').get('Width').value
    assert 1200.0 == mydict.get('DisplaySize').get('Height').value
    print(mydict)


def test_ComplexDict():
    with open('./fixtures/complex_dict.bin', "rb") as f:
        data = f.read()
    mydict = new_string_dict_from_bytes(data)
    assert 3 == len(mydict)
    print(mydict)



