import assert from 'node:assert/strict';
import {buildThirdParties, canonicalActivities, emptyAnswers, exclusive, peopleSuggestions, recoveryTokenFromHash, reviewMarkup, totals, unansweredBooleanActivities, visibleReviewAction} from './wizard.js';

assert.deepEqual(exclusive(['staff','owner_only'],'owner_only'),['owner_only']);
assert.deepEqual(exclusive(['unknown','staff'],'staff'),['staff']);
assert.deepEqual(emptyAnswers().data_channels,[]);
assert.deepEqual(emptyAnswers().third_parties,[]);
assert.equal(emptyAnswers().may_include_minors,null);
assert.equal(emptyAnswers().has_third_parties,null);
const existing=[{id:'kept-id',type:'accountant',relationships:['shared']},{id:'removed-id',type:'legal',relationships:['access']}];
const thirdParties=buildThirdParties(['accountant','technology'],{accountant:['shared'],technology:['access','processed']},existing);
assert.deepEqual(thirdParties,[
  {id:'kept-id',type:'accountant',relationships:['shared']},
  {type:'technology',relationships:['access','processed']},
]);
assert.deepEqual(buildThirdParties(['accountant'],{accountant:['access','unknown']},existing)[0].relationships,['unknown']);
const recovered=unansweredBooleanActivities([
  {id:'yes',answers:{may_include_minors:true,has_third_parties:true}},
  {id:'no',answers:{may_include_minors:false,has_third_parties:false}},
  {id:'pending',answers:{may_include_minors:null,has_third_parties:null}},
]);
assert.deepEqual([...recovered.minors],['pending']);
assert.deepEqual([...recovered.thirdParties],['pending']);
assert.deepEqual(peopleSuggestions('sales','commerce_ecommerce'),['customers','prospects','contacts','company_representatives','users']);
assert.ok(peopleSuggestions('service_delivery','health').includes('patients'));
assert.ok(peopleSuggestions('service_delivery','education_training').includes('students_participants'));
const summary=totals([
  {answers:{people_categories:['customers'],personal_data_types:['contact'],storage_locations:['cloud'],data_channels:[],third_parties:[]}},
  {answers:{people_categories:['customers'],personal_data_types:['contact','identity'],storage_locations:['cloud'],data_channels:['email'],third_parties:[{type:'accountant'}]}}
]);
assert.deepEqual(summary,{activities:2,people_categories:1,personal_data_types:2,storage_locations:1,data_channels:1,third_party_types:1});
console.log('Privacy Data wizard unit checks passed');

assert.equal(recoveryTokenFromHash('#recover=abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-'), 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-');
assert.equal(recoveryTokenFromHash('#recover=short'), null);
assert.equal(recoveryTokenFromHash('#other=value'), null);

const catalog = {
  activity_types: [{code: 'sales', label: 'Ventas'}, {code: 'collaborators', label: 'RRHH'}],
  people_categories: [{code: 'customers', label: 'Clientes'}, {code: 'contacts', label: 'Contactos'}],
  personal_data_types: [{code: 'contact', label: 'Contacto'}, {code: 'tax', label: 'Tributarios'}],
  third_party_types: [
    {code: 'technology_provider', label: 'Proveedor de tecnología'},
    {code: 'hr_labor_provider', label: 'Proveedor de RRHH o remuneraciones'},
    {code: 'client_organization', label: 'Empresa cliente'},
    {code: 'certification_entity', label: 'Entidad certificadora'},
    {code: 'unknown', label: 'No estoy seguro'},
    {code: 'uncertain_alias', label: 'No estoy seguro'},
  ],
};
const activities = [
  {id: 'sales-old', activity_type: 'sales', updated_at: '2026-01-01T00:00:00Z', created_at: '2025-01-01T00:00:00Z', answers: {people_categories: ['customers'], personal_data_types: ['contact']}},
  {id: 'sales-new', activity_type: 'sales', updated_at: '2026-02-01T00:00:00Z', created_at: '2025-01-02T00:00:00Z', answers: {people_categories: ['customers', 'contacts'], personal_data_types: ['contact', 'tax']}},
  {id: 'sales-middle', activity_type: 'sales', updated_at: '2026-01-15T00:00:00Z', created_at: '2025-01-03T00:00:00Z', answers: {}},
];
assert.deepEqual(canonicalActivities(activities).map(activity => activity.id), ['sales-new']);
assert.equal(canonicalActivities([
  {id: 'older', activity_type: 'sales', updated_at: null, created_at: '2025-01-01T00:00:00Z'},
  {id: 'newer', activity_type: 'sales', updated_at: null, created_at: '2025-02-01T00:00:00Z'},
])[0].id, 'newer');
const review = reviewMarkup([
  {code: 'D01', type: 'review', topic: 'Conservación histórica', action: 'Descartar.', activity_id: 'sales-old', activity_type: 'sales'},
  {code: 'D06', type: 'review', topic: 'Menores', action: 'Revisa qué datos de menores manejas y para qué.', activity_id: 'sales-new', activity_type: 'sales'},
  {code: 'D05', type: 'notice', topic: 'Terceros', action: 'Mantén identificados los terceros que participan.', activity_id: 'sales-new', activity_type: 'sales'},
], catalog, activities);
assert.match(review, /Encontramos temas para ordenar en esta actividad\./);
assert.match(review, /Conviene revisar/);
assert.match(review, /Ten presente/);
assert.equal((review.match(/<h2>Ventas<\/h2>/g) || []).length, 1);
assert.match(review, /Menores.*Revisa qué datos de menores manejas y para qué\./);
assert.doesNotMatch(review, /Conservación histórica|Descartar/);
assert.match(review, /<strong>Personas:<\/strong> Clientes · Contactos/);
assert.match(review, /<strong>Datos:<\/strong> Contacto · Tributarios/);
assert.doesNotMatch(review, /D01|D05|technology_provider/);

const contextMarkup = answers => reviewMarkup([
  {code: 'D06', type: 'review', topic: 'Menores', action: 'Revisar.', activity_id: 'context', activity_type: 'sales'},
], catalog, [{id: 'context', activity_type: 'sales', answers}]);
assert.match(contextMarkup({people_categories: ['customers'], personal_data_types: []}), /Personas:.*Clientes/);
assert.doesNotMatch(contextMarkup({people_categories: ['customers'], personal_data_types: []}), /Datos:/);
assert.match(contextMarkup({people_categories: [], personal_data_types: ['contact', 'tax']}), /Datos:.*Contacto · Tributarios/);
assert.doesNotMatch(contextMarkup({people_categories: [], personal_data_types: ['contact']}), /Personas:/);
assert.doesNotMatch(contextMarkup({people_categories: [], personal_data_types: []}), /Personas:|Datos:/);
assert.doesNotMatch(contextMarkup({people_categories: ['missing'], personal_data_types: ['missing']}), /missing|Personas:|Datos:/);

const d04Review = reviewMarkup([
  {code: 'D05', type: 'notice', topic: 'Terceros', action: 'General.', activity_id: 'sales-new', activity_type: 'sales'},
  {code: 'D04', type: 'review', topic: 'Terceros', action: 'Aclara qué información recibe o puede consultar este tercero.', activity_id: 'sales-new', activity_type: 'sales', third_party_type: 'technology_provider'},
], catalog, activities);
assert.match(d04Review, /<strong>Terceros<\/strong> - Aclara qué información recibe o puede consultar el proveedor de tecnología\./);
assert.doesNotMatch(d04Review, /Terceros · Proveedor de tecnología/);
assert.doesNotMatch(d04Review, /General\.|Ten presente/);
const d04 = third_party_type => visibleReviewAction({
  code: 'D04', third_party_type, action: 'Aclara qué información recibe o puede consultar este tercero.',
}, catalog);
assert.equal(d04('hr_labor_provider'), 'Aclara qué información recibe o puede consultar el proveedor de RRHH o remuneraciones.');
assert.equal(d04('client_organization'), 'Aclara qué información recibe o puede consultar la empresa cliente.');
assert.equal(d04('certification_entity'), 'Aclara qué información recibe o puede consultar la entidad certificadora.');
assert.equal(d04('unknown'), 'Aclara qué información recibe o puede consultar este tercero.');
assert.equal(d04('uncertain_alias'), 'Aclara qué información recibe o puede consultar este tercero.');
assert.equal(d04('missing'), 'Aclara qué información recibe o puede consultar este tercero.');
const d05Only = reviewMarkup([
  {code: 'D05', type: 'notice', topic: 'Terceros', action: 'Mantén identificados los terceros que participan.', activity_id: 'sales-new', activity_type: 'sales'},
], catalog, activities);
assert.match(d05Only, /Ten presente.*<strong>Terceros<\/strong> - Mantén identificados los terceros que participan\./);
assert.doesNotMatch(d05Only, /Conviene revisar/);
const rrhh = reviewMarkup([{code: 'D03', type: 'review', topic: 'Accesos', action: 'Identifica.', activity_id: 'rrhh', activity_type: 'collaborators'}], catalog, [{id: 'rrhh', activity_type: 'collaborators', answers: {}}]);
assert.match(rrhh, /RRHH/);
const unknown = reviewMarkup([{code: 'D03', type: 'review', topic: 'Accesos', action: 'Identifica.', activity_id: 'unknown', activity_type: 'sales'}], catalog, [{id: 'unknown', activity_type: 'sales', answers: {people_categories: ['unknown'], personal_data_types: ['unknown']}}]);
assert.doesNotMatch(unknown, />unknown</);
const multiple = reviewMarkup([
  {code: 'D03', type: 'review', topic: 'Accesos', action: 'Identifica.', activity_id: 'sales-new', activity_type: 'sales'},
  {code: 'D03', type: 'review', topic: 'Accesos', action: 'Identifica.', activity_id: 'rrhh', activity_type: 'collaborators'},
], catalog, [...activities, {id: 'rrhh', activity_type: 'collaborators', answers: {}}]);
assert.match(multiple, /Encontramos temas para ordenar en 2 actividades\./);
assert.match(reviewMarkup([], catalog, activities), /No encontramos aspectos pendientes dentro de esta primera revisión\./);
assert.match(reviewMarkup([], catalog, activities), /Esto no significa que exista cumplimiento completo\./);
assert.match(reviewMarkup(null, catalog, activities, {loading: true}), /Revisando tu mapa…/);
const reviewError = reviewMarkup(null, catalog, activities, {error: true});
assert.match(reviewError, /No pudimos completar la revisión del mapa en este momento\./);
assert.match(reviewError, /Reintentar revisión/);
assert.match(reviewMarkup([{type: 'review', topic: '<script>', action: 'A&B', activity_id: 'sales-new', activity_type: 'sales'}], catalog, activities), /&lt;script&gt;.*A&amp;B/);
