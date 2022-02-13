import unittest
import pathlib
import asyncio
import sys

HERE = pathlib.Path(__file__).absolute().parent
CACHE_DIR = HERE.parent / 'cache'
sys.path.append(str(HERE.parent / 'src'))


class TestJson(unittest.TestCase):

    def test_area(self):
        from jma.http_getter import HttpGetter
        import jma

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def test_async():
            getter = HttpGetter(loop, CACHE_DIR)
            area = await getter.get_json_async(jma.AREA_URL)
            assert(area)
            centers = jma.area_tree(area)
            self.assertEqual(11, len(centers))

        loop.run_until_complete(test_async())
        loop.close()


if __name__ == '__main__':
    unittest.main()
