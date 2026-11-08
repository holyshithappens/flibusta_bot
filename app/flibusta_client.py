import os
import aiohttp
from aiohttp_socks import ProxyConnector, ProxyType
from urllib.parse import unquote, urlparse
import re
from bs4 import BeautifulSoup

from .constants import FLIBUSTA_BASE_URL, FLIBUSTA_ONION_URL, FLIBUSTA_TOR_PROXY


class FlibustaClient:
    _base_url: str = FLIBUSTA_BASE_URL
    _onion_url: str = FLIBUSTA_ONION_URL
    _tor_proxy: str = FLIBUSTA_TOR_PROXY

    MODE_DIRECT = "direct"
    MODE_PROXY = "proxy"
    MODE_TOR = "tor"

    DEFAULT_PRIORITY = [MODE_DIRECT, MODE_PROXY, MODE_TOR]

    def __init__(self, username, password, connection_priority: list = None):
        self._session = None
        self._auth_session = None
        self._username = username
        self._password = password
        self._is_logged_in = False
        self._working_mode = None

        if connection_priority is None:
            priority_env = os.getenv("FLIBUSTA_CONNECTION_PRIORITY")
            if priority_env:
                self._connection_priority = [m.strip() for m in priority_env.split(",")]
            else:
                self._connection_priority = self.DEFAULT_PRIORITY
        else:
            self._connection_priority = connection_priority

    def set_connection_priority(self, priority: list):
        valid_modes = {self.MODE_DIRECT, self.MODE_PROXY, self.MODE_TOR}
        if all(m in valid_modes for m in priority):
            self._connection_priority = priority
            self._session = None
            self._auth_session = None
            self._is_logged_in = False
            self._working_mode = None
        else:
            raise ValueError(f"Invalid mode in priority. Valid: {valid_modes}")

    def get_current_base_url(self) -> str:
        mode = self._working_mode or self._connection_priority[0]
        if mode == self.MODE_TOR:
            return self._onion_url
        return self._base_url

    def _get_proxy_config(self, mode: str) -> dict | None:
        if mode == self.MODE_TOR:
            proxy_url = self._tor_proxy
            parsed = urlparse(proxy_url)
            return {
                'proxy_type': ProxyType.SOCKS5,
                'host': parsed.hostname or '127.0.0.1',
                'port': parsed.port or 9050,
                'rdns': True,
                'username': parsed.username,
                'password': parsed.password,
            }
        elif mode == self.MODE_PROXY:
            proxy_url = os.getenv("FLIBUSTA_PROXY")
            if proxy_url:
                parsed = urlparse(proxy_url)
                scheme = parsed.scheme.lower().replace('h', '')
                proxy_type_map = {
                    'socks5': ProxyType.SOCKS5,
                    'socks4': ProxyType.SOCKS4,
                    'http': ProxyType.HTTP,
                    'https': ProxyType.HTTP,
                }
                return {
                    'proxy_type': proxy_type_map.get(scheme, ProxyType.HTTP),
                    'host': parsed.hostname,
                    'port': parsed.port,
                    'rdns': False,
                    'username': parsed.username,
                    'password': parsed.password,
                }
        return None

    async def _create_session_for_mode(self, mode: str, auth: bool = False):
        # Longer timeouts for Tor connections
        if mode == self.MODE_TOR:
            timeout = aiohttp.ClientTimeout(total=300, connect=60, sock_connect=60, sock_read=120)
            test_timeout = aiohttp.ClientTimeout(total=60)
        else:
            timeout = aiohttp.ClientTimeout(total=120, connect=30, sock_connect=30, sock_read=30)
            test_timeout = aiohttp.ClientTimeout(total=10)

        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

        proxy_config = self._get_proxy_config(mode)
        connector = None

        if proxy_config:
            connector = ProxyConnector(
                proxy_type=proxy_config['proxy_type'],
                host=proxy_config['host'],
                port=proxy_config['port'],
                rdns=proxy_config['rdns'],
                username=proxy_config['username'],
                password=proxy_config['password'],
            )
            session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers=headers,
                trust_env=False
            )
        else:
            session = aiohttp.ClientSession(
                timeout=timeout,
                headers=headers,
                trust_env=False
            )

        try:
            test_url = self._onion_url if mode == self.MODE_TOR else self._base_url
            async with session.get(test_url, timeout=test_timeout) as resp:
                if resp.status == 200:
                    print(f"Connection successful via {mode}: {resp.status}")
                    return session
                else:
                    await session.close()
                    if connector:
                        await connector.close()
                    raise Exception(f"Connection test failed with status {resp.status}")
        except Exception as e:
            print(f"Connection failed via {mode} ({e})")
            await session.close()
            if connector:
                await connector.close()
            raise

    async def _create_session(self, auth: bool = False):
        """Try each mode in priority order until one works"""
        for mode in self._connection_priority:
            try:
                session = await self._create_session_for_mode(mode, auth)
                self._working_mode = mode
                return session
            except Exception:
                continue
        raise Exception("All connection modes failed")

    async def _get_session(self, auth=False):
        try:
            if not auth:
                if self._session is None:
                    self._session = await self._create_session()
                test_url = self.get_current_base_url()
                async with self._session.get(test_url) as resp:
                    if resp.status != 200:
                        await self._session.close()
                        self._session = await self._create_session()
                return self._session
            else:
                if self._auth_session is None or not self._is_logged_in:
                    await self.login()
                test_url = self.get_current_base_url()
                async with self._auth_session.get(test_url) as resp:
                    if resp.status != 200:
                        await self.login()
                return self._auth_session
        except Exception as e:
            print(f"Connection error ({e}), recreating session...")
            if not auth:
                if self._session:
                    await self._session.close()
                self._session = await self._create_session()
                return self._session
            else:
                if self._auth_session:
                    await self._auth_session.close()
                await self.login()
                return self._auth_session

    @classmethod
    def get_cover_url_direct(cls, local_cover_url, connection_mode: str = MODE_DIRECT) -> str | None:
        base_url = cls._onion_url if connection_mode == cls.MODE_TOR else cls._base_url
        return f"{base_url}/ib/{local_cover_url}" if local_cover_url else None

    @classmethod
    def get_author_photo_url(cls, local_photo_url, connection_mode: str = MODE_DIRECT) -> str | None:
        base_url = cls._onion_url if connection_mode == cls.MODE_TOR else cls._base_url
        return f"{base_url}/ia/{local_photo_url}" if local_photo_url else None

    @classmethod
    def get_book_url(cls, book_id, connection_mode: str = MODE_DIRECT) -> str | None:
        base_url = cls._onion_url if connection_mode == cls.MODE_TOR else cls._base_url
        return f"{base_url}/b/{book_id}" if book_id else None

    @classmethod
    def get_download_url(cls, book_id, book_format, connection_mode: str = MODE_DIRECT) -> str | None:
        base_url = cls._onion_url if connection_mode == cls.MODE_TOR else cls._base_url
        return f"{base_url}/b/{book_id}/{book_format}" if book_id and book_format else None

    @classmethod
    def get_author_url(cls, author_id, connection_mode: str = MODE_DIRECT) -> str | None:
        base_url = cls._onion_url if connection_mode == cls.MODE_TOR else cls._base_url
        return f"{base_url}/a/{author_id}" if author_id else None

    @classmethod
    def get_translator_url(cls, translator_id, connection_mode: str = MODE_DIRECT) -> str | None:
        base_url = cls._onion_url if connection_mode == cls.MODE_TOR else cls._base_url
        return f"{base_url}/a/{translator_id}" if translator_id else None

    @classmethod
    def get_genre_url(cls, genre_id, connection_mode: str = MODE_DIRECT) -> str | None:
        base_url = cls._onion_url if connection_mode == cls.MODE_TOR else cls._base_url
        return f"{base_url}/g/{genre_id}" if genre_id else None

    @classmethod
    def get_series_url(cls, series_id, connection_mode: str = MODE_DIRECT) -> str | None:
        base_url = cls._onion_url if connection_mode == cls.MODE_TOR else cls._base_url
        return f"{base_url}/s/{series_id}" if series_id else None

    @classmethod
    def get_login_url(cls, connection_mode: str = MODE_DIRECT) -> str:
        base_url = cls._onion_url if connection_mode == cls.MODE_TOR else cls._base_url
        return f"{base_url}/user/login"

    async def login(self):
        try:
            if self._auth_session is None:
                self._auth_session = await self._create_session(auth=True)

            mode = self._working_mode or self._connection_priority[0]
            login_url = self.get_login_url(mode)
            async with self._auth_session.get(login_url) as response:
                html = await response.text()

            form_build_id = None
            if 'form_build_id' in html:
                start = html.find('form_build_id') + len('form_build_id')
                start = html.find('value="', start) + len('value="')
                end = html.find('"', start)
                form_build_id = html[start:end]

            form_data = {
                'name': self._username,
                'pass': self._password,
                'form_id': 'user_login',
                'op': 'Вход в систему',
                'persistent_login': '1'
            }
            if form_build_id:
                form_data['form_build_id'] = form_build_id

            async with self._auth_session.post(login_url, data=form_data) as response:
                result_html = await response.text()

            self._is_logged_in = ('Выйти' in result_html) or (self._username in result_html)
            return self._is_logged_in

        except Exception as e:
            print(f"Authorization error: {e}")
            return False

    async def logout(self):
        if self._auth_session:
            await self._auth_session.close()
            self._auth_session = None
        self._is_logged_in = False

    async def download_book(self, book_id, book_format, auth=False, connection_mode: str = None):
        mode = connection_mode or (self._working_mode or self._connection_priority[0])
        session = await self._get_session(auth)
        download_url = self.get_download_url(book_id, book_format, mode)

        try:
            async with session.get(download_url) as response:
                if response.status != 200:
                    return None, None
                book_data = await response.read()
                content_type = response.headers.get('Content-Type', '')

                if 'html' in content_type:
                    html = await response.text()
                    if 'Страница не найдена' in html:
                        return None, None

                filename = None
                cd = response.headers.get('Content-Disposition')
                if cd:
                    if m := re.search(r'filename[^;=\n]*=([\'"]?)([^\'"\n]+)\1', cd, re.IGNORECASE):
                        filename = unquote(m.group(2))
                return book_data, filename
        except Exception as e:
            print(f"Book download error: {e}")
            return None, None

    async def download_book_resilient(self, book_id, book_format, auth=False):
        modes_to_try = [
            self._working_mode or self._connection_priority[0],
        ] + self._connection_priority

        seen = set()
        unique_modes = [m for m in modes_to_try if not (m in seen or seen.add(m))]

        for mode in unique_modes:
            try:
                book_data, filename = await self.download_book(
                    book_id, book_format, auth, connection_mode=mode
                )
                if book_data:
                    return book_data, filename
            except Exception as e:
                print(f"Download failed via {mode}: {e}")
                continue

        return None, None

    async def close(self):
        if self._session:
            await self._session.close()
        if self._auth_session:
            await self._auth_session.close()

    async def get_book_cover_url(self, book_id: str, connection_mode: str = None):
        mode = connection_mode or self._connection_mode
        try:
            url = self.get_book_url(book_id, mode)
            session = await self._get_session(auth=False)
            cover_url = await self._extract_cover_url_from_page(url, session, mode)
            if cover_url:
                return cover_url
            session = await self._get_session(auth=True)
            return await self._extract_cover_url_from_page(url, session, mode)
        except Exception as e:
            print(f"Cover retrieval error: {e}")
            return None

    async def _extract_cover_url_from_page(self, url, session, connection_mode: str = None):
        async with session.get(url) as response:
            if response.status == 200:
                html_resp = await response.text()
                soup = BeautifulSoup(html_resp, 'html.parser')
                cover_img = soup.find('img', {'title': 'Cover image'})
                if not cover_img:
                    cover_img = soup.find('img', {'alt': 'Cover image'})

                if cover_img and cover_img.get('src'):
                    cover_url = cover_img['src']
                    if not cover_url.startswith('http'):
                        mode = connection_mode or self._working_mode or self._connection_priority[0]
                        base = self._onion_url if mode == self.MODE_TOR else self._base_url
                        cover_url = f"{base}{cover_url}"
                    return cover_url
        return None


flibusta_client = FlibustaClient(os.getenv("FLIBUSTA_USERNAME"), os.getenv("FLIBUSTA_PASSWORD"))