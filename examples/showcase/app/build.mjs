import { createRequire } from 'node:module';
import { pathToFileURL, fileURLToPath } from 'node:url';
import path from 'node:path';
import {existsSync,readdirSync,readFileSync,writeFileSync} from 'node:fs';
const appRoot=path.dirname(fileURLToPath(import.meta.url));
const existing=process.env.DESIGN_RUNTIME_PACKAGE || path.join(appRoot,'package.json');
const require=createRequire(existing);
const {build,createServer}=await import(pathToFileURL(require.resolve('vite')));
const react=(await import(pathToFileURL(require.resolve('@vitejs/plugin-react')))).default;
const tailwind=(await import(pathToFileURL(require.resolve('@tailwindcss/vite')))).default;
const animateCss=require.resolve.paths('tw-animate-css').map(dir=>path.join(dir,'tw-animate-css/dist/tw-animate.css')).find(existsSync);
if(!animateCss)throw new Error('tw-animate-css missing in the explicitly selected runtime');
const aliases=[{find:'@',replacement:path.join(appRoot,'src')},{find:'tailwindcss',replacement:require.resolve('tailwindcss/index.css')},{find:'tw-animate-css',replacement:animateCss}];
for(const name of ['react/jsx-runtime','react/jsx-dev-runtime','react-dom/client','react-dom','react','cn','radix-ui','lucide-react','class-variance-authority']) aliases.push({find:new RegExp('^'+name.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+'$'),replacement:require.resolve(name)});
const config={root:appRoot,configFile:false,base:'./',plugins:[react(),tailwind()],resolve:{alias:aliases,dedupe:['react','react-dom']},build:{outDir:'dist',emptyOutDir:true},server:{host:'127.0.0.1',port:5175,strictPort:true,fs:{allow:[appRoot,path.dirname(existing)]}}};
if(process.argv.includes('--serve')){const server=await createServer(config);await server.listen();server.printUrls();}
else {
 await build(config);
 // Preserve a standard backdrop-filter after the CSS optimizer folds prefixed pairs.
 // Some Chrome versions ignore the Safari-only spelling in the emitted stylesheet.
 const postcss=require('postcss');
 let restored=0;
 function repair(folder){
  for(const entry of readdirSync(folder,{withFileTypes:true})){
   const file=path.join(folder,entry.name);
   if(entry.isDirectory()){repair(file);continue;}
   if(!entry.name.endsWith('.css'))continue;
   const ast=postcss.parse(readFileSync(file,'utf8'),{from:file});
   let changed=false;
   ast.walkDecls('-webkit-backdrop-filter',decl=>{
    if(!decl.parent.nodes.some(node=>node.type==='decl'&&node.prop==='backdrop-filter')){
     decl.cloneAfter({prop:'backdrop-filter'});restored++;changed=true;
    }
   });
   if(changed)writeFileSync(file,ast.toString(),'utf8');
  }
 }
 repair(path.join(appRoot,'dist'));
 console.log(`Restored ${restored} standard backdrop-filter declarations in emitted CSS.`);
}
