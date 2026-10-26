export const AS_OF = '2026-10-19';
export const OWNERS = ['Александра', 'Михаил', 'Дарья'];
export const STAGES = ['Контакт', 'Предложение', 'Переговоры', 'Договор', 'Закрыта'];
export const INITIAL_DEALS = [
 {id:'d1',company:'Форма',initial:'ф',sector:'Архитектура и дизайн',amount:1440000,stage:'Договор',owner:'Александра',due:'2026-10-19',time:'10:30',next_action:'Согласовать финальную версию договора',contact:'Анна Волкова',role:'Директор по развитию',tone:'lime',note:'Клиент подтвердил объём. Осталось согласовать приложение и дату старта.',history:[{date:'16 окт · 15:40',text:'Анна подтвердила состав первого этапа.',kind:'message'},{date:'15 окт · 12:20',text:'Отправлена финальная смета.',kind:'file'}]},
 {id:'d2',company:'Линия',initial:'л',sector:'Финансовые сервисы',amount:960000,stage:'Переговоры',owner:'Михаил',due:'2026-10-18',time:'11:45',next_action:'Провести встречу с финансовым директором',contact:'Илья Белов',role:'Финансовый директор',tone:'blue',note:'На встрече обсудить условия второго платежа.',history:[{date:'16 окт · 11:30',text:'Финансовый директор получил расчёт.',kind:'message'}]},
 {id:'d3',company:'Атлас',initial:'а',sector:'Логистика',amount:640000,stage:'Предложение',owner:'Дарья',due:'2026-10-20',time:'14:00',next_action:'Отправить расчёт второго этапа',contact:'Мария Орлова',role:'Операционный директор',tone:'lavender',note:'Расчёт включает два склада и обучение команды.',history:[{date:'17 окт · 16:10',text:'Уточнены требования к интеграции.',kind:'message'}]},
 {id:'d4',company:'Точка роста',initial:'т',sector:'Образование',amount:380000,stage:'Договор',owner:'Александра',due:'2026-10-19',time:'16:00',next_action:'Получить реквизиты для договора',contact:'Никита Смирнов',role:'Основатель',tone:'peach',note:'Реквизиты обещали прислать после обеда.',history:[{date:'16 окт · 09:40',text:'Никита подтвердил готовность к договору.',kind:'message'}]},
 {id:'d5',company:'Маяк',initial:'м',sector:'Гостеприимство',amount:450000,stage:'Контакт',owner:'Михаил',due:'2026-10-23',time:'12:00',next_action:'Уточнить задачи на знакомстве',contact:'Елена Павлова',role:'Управляющий партнёр',tone:'pink',note:'Первое знакомство: важны текущие процессы команды.',history:[{date:'17 окт · 13:15',text:'Получена заявка на знакомство.',kind:'message'}]},
 {id:'d6',company:'Орбита',initial:'о',sector:'Продуктовая команда',amount:300000,stage:'Предложение',owner:'Дарья',due:'2026-10-26',time:'15:00',next_action:'Подготовить демонстрацию решения',contact:'Артём Соколов',role:'Руководитель продукта',tone:'blue',note:'Демонстрация только на тестовом наборе данных.',history:[{date:'16 окт · 17:20',text:'Команда согласовала сценарий демонстрации.',kind:'file'}]},
 {id:'d7',company:'Место',initial:'м',sector:'Городские пространства',amount:1200000,stage:'Закрыта',owner:'Александра',due:'2026-10-03',time:'10:00',next_action:'Передать проект команде внедрения',contact:'Софья Морозова',role:'Руководитель проекта',tone:'lavender',followupDone:true,note:'Передача завершена.',history:[{date:'3 окт · 10:00',text:'Проект передан команде внедрения.',kind:'check'}]},
 {id:'d8',company:'Контур',initial:'к',sector:'Инженерные решения',amount:720000,stage:'Закрыта',owner:'Михаил',due:'2026-10-08',time:'11:00',next_action:'Назначить стартовую встречу',contact:'Павел Егоров',role:'Коммерческий директор',tone:'peach',followupDone:true,note:'Стартовая встреча назначена.',history:[{date:'8 окт · 11:00',text:'Договор подписан.',kind:'check'}]}
];
export const money = (n) => new Intl.NumberFormat('ru-RU').format(n) + ' ₽';
export const shortMoney = (n) => new Intl.NumberFormat('ru-RU',{maximumFractionDigits:2}).format(n/1000000) + ' млн ₽';
export const dueLabel = (d) => d === AS_OF ? 'Сегодня' : d < AS_OF ? 'Просрочено' : new Intl.DateTimeFormat('ru-RU',{day:'numeric',month:'short'}).format(new Date(d+'T12:00:00'));

export const OPEN_STAGES = STAGES.filter(s=>s!=='Закрыта');
export const CONCEPTS = {
  "hybrid-crm-01": {
    "name": "01 · Lime Desk",
    "eyebrow": "Люди и договорённости",
    "focus": "d1",
    "family": "hybrid"
  },
  "hybrid-crm-02": {
    "name": "02 · Copper Ledger",
    "eyebrow": "Командный реестр",
    "focus": "d2",
    "family": "hybrid"
  },
  "hybrid-crm-03": {
    "name": "03 · Stage Studio",
    "eyebrow": "Воронка команды",
    "focus": "d2",
    "family": "hybrid"
  },
  "hybrid-crm-04": {
    "name": "04 · Amber Agenda",
    "eyebrow": "Повестка рабочего дня",
    "focus": "d1",
    "family": "hybrid"
  },
  "hybrid-crm-05": {
    "name": "05 · Olive Workspace",
    "eyebrow": "Рабочее пространство",
    "focus": "d1",
    "family": "hybrid"
  }
};
