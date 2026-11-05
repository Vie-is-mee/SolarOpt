// Load a src/*.ts module for node:test: transpile it and, recursively, the relative modules it imports at
// run time, so tests exercise the real module graph without a bundler. Type-only imports are erased by
// TypeScript and need no loading. One data: URL per module keeps a single instance of each.
import {readFileSync} from 'node:fs'
import ts from 'typescript'

const urls=new Map()
export function moduleUrl(name){
 if(urls.has(name))return urls.get(name)
 let src=ts.transpileModule(readFileSync(new URL(`../src/${name}.ts`,import.meta.url),'utf8'),{compilerOptions:{module:ts.ModuleKind.ESNext}}).outputText
 for(const dep of new Set([...src.matchAll(/from\s*'\.\/([\w-]+)'/g)].map(m=>m[1])))src=src.replaceAll(`'./${dep}'`,`'${moduleUrl(dep)}'`)
 const url='data:text/javascript;base64,'+Buffer.from(src).toString('base64')
 urls.set(name,url)
 return url
}
export const loadTs=name=>import(moduleUrl(name))
