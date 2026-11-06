import test from 'node:test';
import assert from 'node:assert/strict';
import {validateCreateStep} from '../src/services/createValidation.ts';
const empty={title:'',direction:'',profile:{name:'',email:'',phone:''}};
test('first step rejects empty and whitespace fields before a request',()=>{
 assert.deepEqual(Object.keys(validateCreateStep(0,empty)),['title','direction']);
 assert.deepEqual(Object.keys(validateCreateStep(0,{...empty,title:'  ',direction:'  '})),['title','direction']);
 assert.deepEqual(validateCreateStep(0,{...empty,title:'前端简历',direction:'前端开发'}),{});
});
test('basic information requires name and contact, validates supplied email',()=>{
 const draft={...empty,direction:'前端开发'};
 assert.equal(validateCreateStep(1,draft).name,'请填写姓名');
 assert.ok(validateCreateStep(1,draft).email);
 assert.ok(validateCreateStep(1,{...draft,profile:{name:'张三',email:'bad',phone:''}}).email);
 assert.deepEqual(validateCreateStep(1,{...draft,profile:{name:'张三',email:'test@example.com',phone:''}}),{});
 assert.deepEqual(validateCreateStep(1,{...draft,profile:{name:'张三',email:'',phone:'13800000000'}}),{});
});
