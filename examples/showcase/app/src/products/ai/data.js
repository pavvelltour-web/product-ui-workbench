export const AGENTS = [
 {id:'crm',name:'CRM Assistant',version:'2.4',job:'Документы и сделки',tone:'green'},
 {id:'research',name:'Research',version:'1.8',job:'Поиск и проверка источников',tone:'lilac'},
 {id:'support',name:'Support',version:'3.1',job:'Входящие обращения',tone:'amber'},
];
export const INITIAL_RUNS = [
 {id:'r1',agent:'crm',title:'Подготовить счёт · Форма',target:'Документ INV-1042 · сделка d1',status:'needs_review',time:'10:24',day:18,cost_cents:46,version:'2.4',complete:true,reason:'Создание документа требует вашего решения',payload:'Создать черновик счёта INV-1042 на 144 000 ₽. Получатель: ООО «Форма». Отправка клиенту не запрашивается.',history:['10:24 · Ожидает решения владельца','10:23 · Черновик и реквизиты проверены']},
 {id:'r2',agent:'support',title:'Ответить на обращение #108',target:'Черновик ответа · обращение #108',status:'needs_review',time:'10:18',day:18,cost_cents:12,version:'3.1',complete:false,reason:'Не хватает подтверждённой политики возврата',payload:'Ответ не готов к разрешению: отсутствует источник условия возврата.',history:['10:18 · Неполный контекст: policy_ref отсутствует']},
 {id:'r3',agent:'research',title:'Обновить индекс знаний',target:'Локальный индекс · knowledge-v4',status:'failed',time:'10:12',day:18,cost_cents:9,version:'1.8',complete:true,reason:'Локальное чтение остановлено: источник недоступен',payload:'Повторить только чтение локального источника. Эта проба не выполняет внешних действий.',history:['10:12 · Шаг read_index завершился ошибкой','10:11 · Источник: локальный индекс knowledge-v4']},
 {id:'r4',agent:'crm',title:'Проверить исход отправки',target:'Письмо OUT-078 · сделка d4',status:'unknown',time:'16:40',day:17,cost_cents:33,version:'2.4',complete:false,reason:'Провайдер не подтвердил исход внешнего действия',payload:'Неизвестно, было ли письмо отправлено. Автоматический повтор отключён, чтобы не создать дубль.',history:['17 октября · Отправка: исход неизвестен','17 октября · Подтверждение провайдера отсутствует']},
 {id:'r5',agent:'support',title:'Разобрать входящие обращения',target:'Очередь поддержки · пакет 42',status:'running',time:'10:23',day:18,cost_cents:21,version:'3.1',complete:true,reason:'Классификация 4 из 8 обращений',payload:'Снимок: анализ входящих сообщений. Действия наружу не разрешены.',history:['10:23 · Шаг classify · 4 из 8','10:22 · Пакет принят в обработку']},
 {id:'r6',agent:'crm',title:'Собрать сводку по сделкам',target:'Сводка · 16 октября',status:'completed',time:'09:45',day:16,cost_cents:38,version:'2.4',complete:true,reason:'Сводка сохранена локально',payload:'Сформированы 6 пунктов по активным сделкам. Отправка не выполнялась.',history:['16 октября · Сводка завершена']},
 {id:'r7',agent:'research',title:'Проверить источники отчёта',target:'Отчёт · обзор рынка',status:'completed',time:'14:10',day:15,cost_cents:24,version:'1.8',complete:true,reason:'Проверены 3 локальных источника',payload:'3 источника доступны. Расхождений в локальном примере нет.',history:['15 октября · Проверка завершена']},
 {id:'r8',agent:'support',title:'Подготовить теги обращений',target:'Очередь поддержки · пакет 43',status:'queued',time:'10:26',day:18,cost_cents:0,version:'3.1',complete:true,reason:'Запланирован следующий пакет',payload:'Запуск ещё не начат. Расходы не начислены.',history:['10:26 · Ожидает выполнения']},
];
export const STATE = {
 needs_review:{label:'Нужно решение',short:'Решение',kind:'review'},failed:{label:'Ошибка чтения',short:'Ошибка',kind:'error'},unknown:{label:'Исход неизвестен',short:'Неизвестен',kind:'unknown'},running:{label:'В работе',short:'В работе',kind:'running'},completed:{label:'Завершён',short:'Завершён',kind:'done'},queued:{label:'В очереди',short:'В очереди',kind:'queued'},approved:{label:'Разрешён локально',short:'Разрешён',kind:'done'},rejected:{label:'Отклонён',short:'Отклонён',kind:'queued'},
};
export const BASE_TRACE = [
 {name:'Задание принято',type:'Ввод',detail:'Создать черновик счёта для сделки d1',state:'done',time:'10:23:02'},
 {name:'Карточка сделки прочитана',type:'Чтение',detail:'Форма · d1 · реквизиты присутствуют',state:'done',time:'10:23:04'},
 {name:'Реквизиты сопоставлены',type:'Проверка',detail:'ООО «Форма» · совпадение источника',state:'done',time:'10:23:05'},
 {name:'Черновик подготовлен',type:'Документ',detail:'INV-1042 · 144 000 ₽ · без отправки',state:'done',time:'10:23:08'},
 {name:'Решение владельца',type:'Контроль',detail:'Ожидание разрешения на создание',state:'current',time:'10:24:00'},
 {name:'Сохранить черновик',type:'Действие',detail:'Только после точного разрешения',state:'waiting',time:'—'},
];
export const dollars = cents => new Intl.NumberFormat('en-US',{style:'currency',currency:'USD'}).format(cents/100);
