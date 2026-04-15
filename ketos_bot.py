2026-04-15 19:54:17,308 (__init__.py:1254 MainThread) ERROR - TeleBot: "Threaded polling exception: A request to the Telegram API was unsuccessful. Error code: 409. Description: Conflict: terminated by other getUpdates request; make sure that only one bot instance is running"
2026-04-15 19:54:17,310 (__init__.py:1256 MainThread) ERROR - TeleBot: "Exception traceback:
Traceback (most recent call last):
  File "C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\telebot\__init__.py", line 1247, in __threaded_polling
    polling_thread.raise_exceptions()
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\telebot\util.py", line 116, in raise_exceptions
    raise self.exception_info
  File "C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\telebot\util.py", line 98, in run
    task(*args, **kwargs)
    ~~~~^^^^^^^^^^^^^^^^^
  File "C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\telebot\__init__.py", line 689, in __retrieve_updates
    updates = self.get_updates(offset=(self.last_update_id + 1),
                               allowed_updates=allowed_updates,
                               timeout=timeout, long_polling_timeout=long_polling_timeout)
  File "C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\telebot\__init__.py", line 661, in get_updates
    json_updates = apihelper.get_updates(
        self.token, offset=offset, limit=limit, timeout=timeout, allowed_updates=allowed_updates,
        long_polling_timeout=long_polling_timeout)
  File "C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\telebot\apihelper.py", line 339, in get_updates
    return _make_request(token, method_url, params=payload)
  File "C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\telebot\apihelper.py", line 168, in _make_request
    json_result = _check_result(method_name, result)
  File "C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\telebot\apihelper.py", line 197, in _check_result
    raise ApiTelegramException(method_name, result, result_json)
telebot.apihelper.ApiTelegramException: A request to the Telegram API was unsuccessful. Error code: 409. Description: Conflict: terminated by other getUpdates request; make sure that only one bot instance is running
"
2026-04-15 19:54:21,323 (__init__.py:1254 MainThread) ERROR - TeleBot: "Threaded polling exception: A request to the Telegram API was unsuccessful. Error code: 409. Description: Conflict: terminated by other getUpdates request; make sure that only one bot instance is running"
2026-04-15 19:54:21,327 (__init__.py:1256 MainThread) ERROR - TeleBot: "Exception traceback:
Traceback (most recent call last):
  File "C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\telebot\__init__.py", line 1247, in __threaded_polling
    polling_thread.raise_exceptions()
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\telebot\util.py", line 116, in raise_exceptions
    raise self.exception_info
  File "C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\telebot\util.py", line 98, in run
    task(*args, **kwargs)
    ~~~~^^^^^^^^^^^^^^^^^
  File "C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\telebot\__init__.py", line 689, in __retrieve_updates
    updates = self.get_updates(offset=(self.last_update_id + 1),
                               allowed_updates=allowed_updates,
                               timeout=timeout, long_polling_timeout=long_polling_timeout)
  File "C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\telebot\__init__.py", line 661, in get_updates
    json_updates = apihelper.get_updates(
        self.token, offset=offset, limit=limit, timeout=timeout, allowed_updates=allowed_updates,
        long_polling_timeout=long_polling_timeout)
  File "C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\telebot\apihelper.py", line 339, in get_updates
    return _make_request(token, method_url, params=payload)
  File "C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\telebot\apihelper.py", line 168, in _make_request
    json_result = _check_result(method_name, result)
  File "C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\telebot\apihelper.py", line 197, in _check_result
    raise ApiTelegramException(method_name, result, result_json)
telebot.apihelper.ApiTelegramException: A request to the Telegram API was unsuccessful. Error code: 409. Description: Conflict: terminated by other getUpdates request; make sure that only one bot instance is running
"
2026-04-15 19:54:26,041 (__init__.py:1254 MainThread) ERROR - TeleBot: "Threaded polling exception: A request to the Telegram API was unsuccessful. Error code: 409. Description: Conflict: terminated by other getUpdates request; make sure that only one bot instance is running"
2026-04-15 19:54:26,045 (__init__.py:1256 MainThread) ERROR - TeleBot: "Exception traceback:
Traceback (most recent call last):
  File "C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\telebot\__init__.py", line 1247, in __threaded_polling
    polling_thread.raise_exceptions()
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\telebot\util.py", line 116, in raise_exceptions
    raise self.exception_info
  File "C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\telebot\util.py", line 98, in run
    task(*args, **kwargs)
    ~~~~^^^^^^^^^^^^^^^^^
  File "C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\telebot\__init__.py", line 689, in __retrieve_updates
    updates = self.get_updates(offset=(self.last_update_id + 1),
                               allowed_updates=allowed_updates,
                               timeout=timeout, long_polling_timeout=long_polling_timeout)
  File "C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\telebot\__init__.py", line 661, in get_updates
    json_updates = apihelper.get_updates(
        self.token, offset=offset, limit=limit, timeout=timeout, allowed_updates=allowed_updates,
        long_polling_timeout=long_polling_timeout)
  File "C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\telebot\apihelper.py", line 339, in get_updates
    return _make_request(token, method_url, params=payload)
  File "C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\telebot\apihelper.py", line 168, in _make_request
    json_result = _check_result(method_name, result)
  File "C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\telebot\apihelper.py", line 197, in _check_result
    raise ApiTelegramException(method_name, result, result_json)
telebot.apihelper.ApiTelegramException: A request to the Telegram API was unsuccessful. Error code: 409. Description: Conflict: terminated by other getUpdates request; make sure that only one bot instance is running
"
2026-04-15 19:54:32,278 (__init__.py:1254 MainThread) ERROR - TeleBot: "Threaded polling exception: A request to the Telegram API was unsuccessful. Error code: 409. Description: Conflict: terminated by other getUpdates request; make sure that only one bot instance is running"
2026-04-15 19:54:32,280 (__init__.py:1256 MainThread) ERROR - TeleBot: "Exception traceback:
Traceback (most recent call last):
  File "C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\telebot\__init__.py", line 1247, in __threaded_polling
    polling_thread.raise_exceptions()
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\telebot\util.py", line 116, in raise_exceptions
    raise self.exception_info
  File "C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\telebot\util.py", line 98, in run
    task(*args, **kwargs)
    ~~~~^^^^^^^^^^^^^^^^^
  File "C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\telebot\__init__.py", line 689, in __retrieve_updates
    updates = self.get_updates(offset=(self.last_update_id + 1),
                               allowed_updates=allowed_updates,
                               timeout=timeout, long_polling_timeout=long_polling_timeout)
  File "C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\telebot\__init__.py", line 661, in get_updates
    json_updates = apihelper.get_updates(
        self.token, offset=offset, limit=limit, timeout=timeout, allowed_updates=allowed_updates,
        long_polling_timeout=long_polling_timeout)
  File "C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\telebot\apihelper.py", line 339, in get_updates
    return _make_request(token, method_url, params=payload)
  File "C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\telebot\apihelper.py", line 168, in _make_request
    json_result = _check_result(method_name, result)
  File "C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\telebot\apihelper.py", line 197, in _check_result
    raise ApiTelegramException(method_name, result, result_json)
telebot.apihelper.ApiTelegramException: A request to the Telegram API was unsuccessful. Error code: 409. Description: Conflict: terminated by other getUpdates request; make sure that only one bot instance is running
"
2026-04-15 19:54:38,508 (__init__.py:1254 MainThread) ERROR - TeleBot: "Threaded polling exception: A request to the Telegram API was unsuccessful. Error code: 409. Description: Conflict: terminated by other getUpdates request; make sure that only one bot instance is running"
2026-04-15 19:54:38,511 (__init__.py:1256 MainThread) ERROR - TeleBot: "Exception traceback:
Traceback (most recent call last):
  File "C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\telebot\__init__.py", line 1247, in __threaded_polling
    polling_thread.raise_exceptions()
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\telebot\util.py", line 116, in raise_exceptions
    raise self.exception_info
  File "C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\telebot\util.py", line 98, in run
    task(*args, **kwargs)
    ~~~~^^^^^^^^^^^^^^^^^
  File "C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\telebot\__init__.py", line 689, in __retrieve_updates
    updates = self.get_updates(offset=(self.last_update_id + 1),
                               allowed_updates=allowed_updates,
                               timeout=timeout, long_polling_timeout=long_polling_timeout)
  File "C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\telebot\__init__.py", line 661, in get_updates
    json_updates = apihelper.get_updates(
        self.token, offset=offset, limit=limit, timeout=timeout, allowed_updates=allowed_updates,
        long_polling_timeout=long_polling_timeout)
  File "C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\telebot\apihelper.py", line 339, in get_updates
    return _make_request(token, method_url, params=payload)
  File "C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\telebot\apihelper.py", line 168, in _make_request
    json_result = _check_result(method_name, result)
  File "C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\telebot\apihelper.py", line 197, in _check_result
    raise ApiTelegramException(method_name, result, result_json)
telebot.apihelper.ApiTelegramException: A request to the Telegram API was unsuccessful. Error code: 409. Description: Conflict: terminated by other getUpdates request; make sure that only one bot instance is running
"
2026-04-15 19:54:50,728 (__init__.py:1254 MainThread) ERROR - TeleBot: "Threaded polling exception: A request to the Telegram API was unsuccessful. Error code: 409. Description: Conflict: terminated by other getUpdates request; make sure that only one bot instance is running"
2026-04-15 19:54:50,731 (__init__.py:1256 MainThread) ERROR - TeleBot: "Exception traceback:
Traceback (most recent call last):
  File "C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\telebot\__init__.py", line 1247, in __threaded_polling
    polling_thread.raise_exceptions()
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\telebot\util.py", line 116, in raise_exceptions
    raise self.exception_info
  File "C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\telebot\util.py", line 98, in run
    task(*args, **kwargs)
    ~~~~^^^^^^^^^^^^^^^^^
  File "C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\telebot\__init__.py", line 689, in __retrieve_updates
    updates = self.get_updates(offset=(self.last_update_id + 1),
                               allowed_updates=allowed_updates,
                               timeout=timeout, long_polling_timeout=long_polling_timeout)
  File "C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\telebot\__init__.py", line 661, in get_updates
    json_updates = apihelper.get_updates(
        self.token, offset=offset, limit=limit, timeout=timeout, allowed_updates=allowed_updates,
        long_polling_timeout=long_polling_timeout)
  File "C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\telebot\apihelper.py", line 339, in get_updates
    return _make_request(token, method_url, params=payload)
  File "C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\telebot\apihelper.py", line 168, in _make_request
    json_result = _check_result(method_name, result)
  File "C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\telebot\apihelper.py", line 197, in _check_result
    raise ApiTelegramException(method_name, result, result_json)
telebot.apihelper.ApiTelegramException: A request to the Telegram API was unsuccessful. Error code: 409. Description: Conflict: terminated by other getUpdates request; make sure that only one bot instance is running
"
