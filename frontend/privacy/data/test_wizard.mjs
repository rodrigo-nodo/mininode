import assert from 'node:assert/strict';
import {buildThirdParties, emptyAnswers, exclusive, totals} from './wizard.js';

assert.deepEqual(exclusive(['staff','owner_only'],'owner_only'),['owner_only']);
assert.deepEqual(exclusive(['unknown','staff'],'staff'),['staff']);
assert.deepEqual(emptyAnswers().data_channels,[]);
assert.deepEqual(emptyAnswers().third_parties,[]);
const existing=[{id:'kept-id',type:'accountant',relationships:['shared']},{id:'removed-id',type:'legal',relationships:['access']}];
const thirdParties=buildThirdParties(['accountant','technology'],{accountant:['shared'],technology:['access','processed']},existing);
assert.deepEqual(thirdParties,[
  {id:'kept-id',type:'accountant',relationships:['shared']},
  {type:'technology',relationships:['access','processed']},
]);
assert.deepEqual(buildThirdParties(['accountant'],{accountant:['access','unknown']},existing)[0].relationships,['unknown']);
const summary=totals([
  {answers:{people_categories:['customers'],personal_data_types:['contact'],storage_locations:['cloud'],data_channels:[],third_parties:[]}},
  {answers:{people_categories:['customers'],personal_data_types:['contact','identity'],storage_locations:['cloud'],data_channels:['email'],third_parties:[{type:'accountant'}]}}
]);
assert.deepEqual(summary,{activities:2,people_categories:1,personal_data_types:2,storage_locations:1,data_channels:1,third_party_types:1});
console.log('Privacy Data wizard unit checks passed');
