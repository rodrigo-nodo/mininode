import assert from 'node:assert/strict';
import {buildThirdParties, emptyAnswers, exclusive, peopleSuggestions, recoveryTokenFromHash, reviewMarkup, totals, unansweredBooleanActivities} from './wizard.js';

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

const renderedReview = reviewMarkup([
  {type: 'review', title: 'Revisar acceso', description: 'Descripción', activity_type: 'sales'},
  {type: 'notice', title: 'Hay terceros', description: 'Descripción', activity_type: 'sales'},
], () => 'Ventas', () => 'Proveedor');
assert.match(renderedReview, /Conviene revisar/);
assert.match(renderedReview, /Ten presente/);
assert.match(renderedReview, /Ventas/);
assert.match(reviewMarkup([], () => '', () => ''), /No encontramos aspectos pendientes/);
