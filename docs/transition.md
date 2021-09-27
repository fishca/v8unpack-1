#Переход на сборку из одних исходников

## Сборка внешней обработки для разных платформ из одних исходников

Предположим на входе есть три обработки сделанные когда-то для для 8.1, 8.2 и 8.3.
Эти обработки по сути делают одно и то же, просто сделаны для разных платформ.
Код в этих обработках писался под 8.3, и затем переносился и адаптировался под старые
версии платформ.

В основном он отличается наличием директив и незначительными особенностями платформ. 

    Под 8.2 и 8.3 здесь и далее имеется ввиду обычные (82) и управляемые (83+) формы.
    Такая разбивка потому, что версия формата исходников имеет схожую струтуру, кто ме
    того требуется чтобы обычные формы работали на самых старых платформах 8.2+, а это
    только 8.2.
    
Основной сложностью объединения являются разные идентификаторы объектов (самой обработки, 
форм и макетов. 

На выходе мы хотим получить четыре репозитория с исходным кодом, 3 для каждой из версий
платформы, четвертый для субмодуля который будет использоваться в версиях и содержащем
общий код, макеты и саму структуру обработки.

Порядок действий:

### Причесываем обработку

В комментарии макетов содержих файлы, ставим первым словом расширение файла

В код добавляем [области](code.md)) которые хотим хранить в отдельных файлах.

### Создаем репозиторий для 83

Создаем репозиторий для 83 и для core.

Клонируем репозиторий 83 на диск, и добавляем в него субмодуль core

В папку bin кладем обработку.

В корне создаем коммандные файлых для облегчения себе жизни и index.json, где будем описывать какие файлы 
у нас общие.

extract.cmd
    
    v8unpack.exe -E bin\Sbis1C_UF.epf src --index index.json

build.cmd
    
    v8unpack.exe -B src bin\Sbis1C_UF.epf --index index.json --version=83

update_index.cmd - для формирования и обновления индекса

    v8unpack.exe -I index.json src core

index.json

    {}

В итоге имеем:

    >core            - папка подмодуля для общих файлов
    >bin             - папка для собранных бинарников 
        Sbis1C_UF.epf
    >src             - папка где будут исходники
        тут красота
    build.cmd        - запускалка сборки
    extract.cmd      - запускалка разборки
    update_index.cmd - формирования и обновления индекса
    index.json       - словарь общих файлов


### 2.Распаковываем
Запускаем extract.cmd в результате в src появились исходники.

Запускаем update_index.cmd в результате заполнился index.json и в него попали все файлы, и по умолчанию
они все выставились как будтно они общие и должны лежать в core. Если сейчас ещё раз запустить разборку
то они там все и окажутся. 

Редактируем index.json - у того, что не должно быть в core меняем значение на пустое "". Удялть лишние
ключи смысла нет. При последующих запусках index_update он добавит все чего нет, а то что уже есть трогать не будет.
Как альтернатива, формировать index.json руками или как то ещё.

В нашем случае в core уезжает почти всё (код, формы, макеты), в 83 остаются только разметка 83 - файлы 
оканчивающиеся на *83.json

Итого определились где что должно лежать, распаковали бинарник ещё раз - теперь имеем исходники в нужном виде.

Пробуем собрать и проверить открыв собранный файл в 1С (на всякий случай имеем копию бинарника).

Если все получилось - коммитим. Ура! Самое простое позади.  

### 3. Объединяем с 82

Как мы помним изначальной задачей является переиспользование максимально возможного кода, в нашем случае
у нас полностью одинаковое количество, название и тип ресурсов (макеты, формы).

На текущий момент уровень разбора метаданных достаточно низкий, по сути каждый объект метажанных состоит из
заголовка, ссылок на вложенные объекты, значений свойств (в т.ч. разметка форм) и данных (двоичные данные макета или
программный код). На текущий момент парсер лишь разделяет файлы на эти участки.

Повторяем все тоже самое как делали для 83, только не забываем в коммандном файле сборки
поменять номер собираемой версии на 82.  

Отдельные типы объектов генерятся полностью, например макеты и их можно объединить. Для этого нужно заменить uuid 
макета 82 на uuid от макета 83 везде где он встречается в исходниках.

Повторяем для 81.

Тадам и через пару недель стало жить чуть легче. 
