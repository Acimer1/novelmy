<script setup>
import {ref} from 'vue'
const props=defineProps({text:String,label:String}), message=ref('')
async function copy(){try{if(navigator.clipboard?.writeText)await navigator.clipboard.writeText(props.text);else{const field=document.createElement('textarea');field.value=props.text;field.style.position='fixed';field.style.opacity='0';document.body.append(field);field.select();try{if(!document.execCommand('copy'))throw Error()}finally{field.remove()}}message.value='已复制'}catch{message.value='复制失败，请手动复制'}}
</script><template><button type="button" @click="copy">{{label||'复制'}}</button><small role="status">{{message}}</small></template>
