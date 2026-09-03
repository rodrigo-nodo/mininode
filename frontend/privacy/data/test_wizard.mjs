import assert from 'node:assert/strict';
import {activityContext, buildThirdParties, deduplicateThirdPartyObservations, emptyAnswers, exclusive, groupReviewByActivity, peopleSuggestions, recoveryTokenFromHash, reviewMarkup, totals, unansweredBooleanActivities} from './wizard.js';

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
  activity_types: [{code: 'sales', label: 'Ventas'}, {code: 'collaborators', label: 'Gestión de trabajadores'}],
  people_categories: [{code: 'customers', label: 'Clientes'}, {code: 'employees', label: 'Trabajadores'}],
  personal_data_types: [{code: 'contact', label: 'Contacto'}, {code: 'billing', label: 'Facturación'}],
  third_party_types: [{code: 'technology_provider', label: 'Proveedor de tecnología'}],
};
const activities = [
  {id: 'sales-id', activity_type: 'sales', answers: {people_categories: ['customers'], personal_data_types: ['contact', 'billing']}},
  {id: 'staff-id', activity_type: 'collaborators', answers: {people_categories: ['employees'], personal_data_types: []}},
];
const observations = [
  {code: 'D01', type: 'review', topic: 'Conservación', action: 'Define cuánto tiempo.', title: 'Título legacy', description: 'Descripción legacy', activity_id: 'sales-id', activity_type: 'sales'},
  {code: 'D03', type: 'review', topic: 'Accesos', action: 'Identifica quién accede.', activity_id: 'sales-id', activity_type: 'sales'},
  {code: 'D05', type: 'notice', topic: 'Terceros general', action: 'Mantén identificados los terceros.', activity_id: 'sales-id', activity_type: 'sales'},
  {code: 'D04', type: 'notice', topic: 'Terceros', action: 'Aclara qué información recibe o puede consultar este tercero.', activity_id: 'sales-id', activity_type: 'sales', third_party_type: 'technology_provider'},
  {code: 'D03', type: 'review', topic: 'Accesos', action: 'Limita los accesos.', activity_id: 'staff-id', activity_type: 'collaborators'},
];
assert.equal(groupReviewByActivity(observations, activities).length, 2);
assert.equal(groupReviewByActivity(observations, activities)[0].observations.length, 4);
assert.deepEqual(activityContext(activities[0], catalog), ['Clientes', 'Contacto', 'Facturación']);
assert.deepEqual(activityContext(activities[1], catalog), ['Trabajadores']);
assert.deepEqual(activityContext({answers: {people_categories: [], personal_data_types: ['contact', 'billing']}}, catalog), ['Contacto', 'Facturación']);
assert.deepEqual(activityContext({answers: {people_categories: [], personal_data_types: []}}, catalog), []);
assert.deepEqual(deduplicateThirdPartyObservations(observations.slice(0, 4)).map(item => item.code), ['D01', 'D03', 'D04']);
assert.deepEqual(deduplicateThirdPartyObservations([observations[2]]).map(item => item.code), ['D05']);

const review = reviewMarkup(observations, catalog, activities);
assert.match(review, /Encontramos temas para ordenar en 2 actividades\./);
assert.equal((review.match(/<h3>Ventas<\/h3>/g) || []).length, 1);
assert.match(review, /Clientes · Contacto · Facturación/);
assert.match(review, /Trabajadores/);
assert.match(review, /Conviene revisar/);
assert.match(review, /Ten presente/);
assert.match(review, /<strong>Conservación<\/strong>.*Define cuánto tiempo\./);
assert.match(review, /Aclara qué información recibe o puede consultar el proveedor de tecnología\./);
assert.doesNotMatch(review, /Título legacy|Descripción legacy|D0[1-6]|Terceros general|sales|technology_provider/);

const singleReview = reviewMarkup([observations[0]], catalog, activities);
assert.match(singleReview, /Encontramos temas para ordenar en esta actividad\./);
assert.doesNotMatch(singleReview, /Ten presente/);
const noticeOnly = reviewMarkup([observations[2]], catalog, activities);
assert.match(noticeOnly, /Terceros general/);
assert.doesNotMatch(noticeOnly, /Conviene revisar/);
const contextless = reviewMarkup([{...observations[0], activity_id: 'empty'}], catalog, [{id: 'empty', activity_type: 'sales', answers: {}}]);
assert.doesNotMatch(contextless, /pd-review-activity__context/);
assert.match(reviewMarkup([], catalog), /No encontramos aspectos pendientes dentro de esta primera revisión\./);
assert.match(reviewMarkup([], catalog), /Esto no significa que exista cumplimiento completo\./);
assert.match(reviewMarkup(null, catalog, [], {loading: true}), /Revisando tu mapa…/);
const reviewError = reviewMarkup(null, catalog, [], {error: true});
assert.match(reviewError, /No pudimos completar la revisión del mapa en este momento\./);
assert.match(reviewError, /Reintentar revisión/);
const escaped = reviewMarkup([{code: 'D01', type: 'review', topic: '<script>', action: 'A&B', activity_id: 'sales-id', activity_type: 'sales'}], catalog, activities);
assert.match(escaped, /&lt;script&gt;.*A&amp;B/);
assert.doesNotMatch(escaped, /<script>/);
