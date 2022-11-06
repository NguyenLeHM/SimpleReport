from fpdf import FPDF
import sqlite3 as sql
from html.parser import HTMLParser

class MyHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.lstAllTags=[]
        self.lstTagTexts=[]
        self.lstKeyTexts=[]
        self.lstKeys=[]
        self.dicData={}
        self.intLevel=0
        self.curTagkey=''
        self.curTag=''
        self.textAll=''
        self.dicAttrs={}
        self.lstKeyParents=[]
        self.lstParents=[]

    def handle_starttag(self, tag, attrs):
        self.intLevel+=1
        if tag not in self.lstKeyParents:
             self.lstKeyParents.append(tag)
        
        intCount=len(self.lstKeyParents)
        if intCount>1:
            keyParent=self.lstKeyParents[intCount-2]
            self.lstParents.append([tag,keyParent])           
        
        self.curTag=tag
        self.lstKeys.append(tag)
        if tag not in self.lstKeys:
            intOrder=1
        else:
            intOrder=self.lstKeys.count(tag)
        self.curTagkey=tag+str(self.intLevel).rjust(3,'0')+str(intOrder).rjust(3,"0")
        self.lstAllTags.append([tag,self.intLevel,intOrder,self.curTagkey])
        self.textAll+="<".rjust((self.intLevel-1)*4," ")+tag+">\n"
        dicAttr={}
        for attr in attrs:
            dicAttr[attr[0]]=attr[1]
        if dicAttr!={}:
            self.dicAttrs[tag]=dicAttr
        
    def handle_endtag(self, tag):
        self.textAll+="</".rjust((self.intLevel-1)*4," ")+tag+">\n"
        self.intLevel-=1
        self.curTagkey=''
        self.lstKeyParents.remove(tag)

    def handle_data(self, data):
        if self.curTag not in self.lstKeyTexts:
            self.lstKeyTexts.append(self.curTag)
            self.lstTagTexts.append([self.curTag,data])
        self.textAll+=''.rjust(self.intLevel*4," ")+data+'\n'
        self.dicData[self.curTagkey]=data

parser=MyHTMLParser()
pdf=FPDF()
lstParents=[]
dicAttrs={}
fontset={}
pageset={}
dicTables={}
dicParameters={}
dicVariables={}
dicCalculates={}
dicGroups={}
tableset=''
dbms='einvoice.db'

def connectdb():
    connectdata = sql.connect(dbms)
    connectdata.row_factory = sql.Row
    return connectdata
    
def GetRows(tblName,fldNames,strWhere='1=1'):
    try:
        conn=connectdb()
        with conn:
            sqlcmd = "Select " + fldNames + " from " + tblName + " where " + strWhere
            curs = conn.cursor()
            curs.execute(sqlcmd)
            rows=curs.fetchall()
        conn.close()
        return rows
    except:
        return None

def StrFloat(floatVar,decimal=0):
    floatVar=round(floatVar*100)/100
    lstValue=str(floatVar).split('.')
    if decimal==0:
        strDecimal=""
    else:
        strDecimal=","+lstValue[1].ljust(decimal,'0')[:decimal]
    strNumber=lstValue[0]
    groups = []
    while strNumber and strNumber[-1].isdigit():
        groups.append(strNumber[-3:])
        strNumber = strNumber[:-3]
    return strNumber + '.'.join(reversed(groups)) + strDecimal

def GetChilds(tagname):
    global lstParents, lstResults
    lstFilters = list(filter(lambda c: c[1]==tagname, lstParents))
    if len(lstFilters)>0:
        for item in lstFilters:
            itemname=item[0]
            lstResults.append(itemname)
            GetChilds(itemname)
    return lstResults

def GetAttributes(tagname):
    global dicAttrs
    try:
        dicResults=dicAttrs[tagname]
    except:
        dicResults={}
    return dicResults

def GetAttribute(tagname,*args):
    dicAttributes=GetAttributes(tagname)
    lstResults=[]
    for attr in args:
        try:
            lstResults.append(dicAttributes[attr]) 
        except:
            lstResults.append(None)
    return lstResults

def InitVariable():
    global dicVariable, lstResults
    lstResults=[]
    lstVariables=GetChilds('variable')
    for variable in lstVariables:
        initvalue,expression,calculate,resetwhen=GetAttribute(variable,'init','expression','calculate','reset')
        dicVariable={}
        dicVariable['initvalue']=int(initvalue)
        dicVariable['expression']=expression
        dicVariable['calculate']=calculate
        dicVariable['resetwhen']=resetwhen
        dicVariable['value']=int(initvalue)
        dicVariables[variable]=dicVariable

def CalcVariable(row):
    global dicVariable, dicCalculates, lstResults
    lstResults=[]
    lstVariables=GetChilds('variable')
    for variable in lstVariables:
        dicVariable=dicVariables[variable]
        expression=dicVariable['expression']
        calculate=dicVariable['calculate']
        oldvalue=dicVariable['value']
        newvalue=CalcExpression(expression,row)
        if calculate in ['SUM','COUNT','MAX','MIN']:
            value=Calculate(variable,calculate,newvalue,oldvalue)
        else:
            value=newvalue
        dicVariable['value']=value
        dicVariables[variable]=dicVariable

def CalcCaculate(row):
    global dicCalculates,lstResults
    lstResults=[]
    lstChilds=GetChilds('report')
    for child in lstChilds:
        expression, calculate = GetAttribute(child,'expression','calculate')
        if calculate in ['SUM','COUNT','MAX','MIN']:
            newvalue=CalcExpression(expression,row)
            value=Calculate(child,calculate,newvalue)
            dicCalculate=dicCalculates[child]
            dicCalculate['value']=value
            dicCalculates[child]=dicCalculate

def Calculate(nameobject,func,newvalue,oldvalue=None):
    global dicCalculates
    dicCalculate=dicCalculates[nameobject]
    if not oldvalue:
        oldvalue=dicCalculate['value']
    func=func.upper()
    value=newvalue
    if func in ['SUM','COUNT','MAX',"MIN"]:
        if func=='SUM':
            value=oldvalue+newvalue
        elif func=='COUNT':
            value=oldvalue+1
        elif func=='MAX':
            if oldvalue>newvalue: 
                value=oldvalue
        elif func=='MIN':
            if oldvalue<newvalue: 
                value=oldvalue
    return value

def GetVariable(varname):
    global dicVariables
    dicVariable=dicVariables[varname]
    return dicVariable['value']

def GetParameter(varname):
    global dicParameters
    value=dicParameters[varname]
    return value

def ResetVariable(resetwhen):
    global dicVariables
    for variable in dicVariables:
        dicVariable=dicVariables[variable]
        if dicVariable['resetwhen']==resetwhen:
            dicVariable['value']=dicVariable['initvalue']
            dicVariables[variable]=dicVariable

def DrawBand(nameband,row=None):
    bandheight,_=GetAttribute(nameband,'height',None)
    if bandheight:       
        bandheight=float(bandheight)
        MaxY=0
        global pageset, fontset, lstParents, lstResults
        lstResults=[]    
        lstChilds=GetChilds(nameband)
        #calculate height object
        if row:
            for child in lstChilds:
                nameclass, stretch, position, expression, width, height, font = GetAttribute(child,'class','stretch','position','expression','width','height','font')
                if nameclass=='Field':
                    if stretch:
                        if not height:
                            height=20
                        else:
                            height=float(height)
                        if not width:
                            width=80
                        else:
                            width=float(width)
                        if not font:
                            font=[fontset['name'],fontset['style'],fontset['size']]
                        else:
                            font=font.split(',')
                            font=[font[0],font[1],int(font[2])]
                        if not position:
                            position=[0,0]
                        else:
                            position=position.split(',')
                            position=[float(position[0]),float(position[1])] 
                        text = CalcExpression(expression,row)       
                        #text = row[expression]
                        texts = WrapText(text,width,font) 
                        height = (len(texts)-1)*height+ position[1]
                        if height>bandheight:
                            bandheight=height
        
        #check new page
        pageno, x, y = [pageset['pageno'],pageset['x'],pageset['y']]
        if pageset['height']<y+bandheight:
            DrawBand('footer')
            global pdf
            pdf.showPage()
            NewPage()
        #check new 
        CheckNewGroup(row)
        #output
        for child in lstChilds:
            pageno, x, y = [pageset['pageno'],pageset['x'],pageset['y']]
            lastY=DrawObject(child,bandheight,pageno,x,y,row)
            if lastY>MaxY:
                MaxY=lastY
        
        y = pageset['y']
        if MaxY>y:
            pageset['y']=MaxY

def DrawObject(nameobject,bandheight,pageno,x,y,row):
    MaxY=0
    global pagesetup, fontset
    nameclass, position, width, height, text, border, align, font, stretch, expression, calcualte, linebreak = GetAttribute(nameobject,'class','position','width','height','text','border','align','font','stretch','expression','calculate','linebreak')
    if not align:
        align='Left'
    if not border or border=='0':
        border=0
    elif border=='1':
        border=1 
    if font:
        font=font.split(',')
        font=[font[0],font[1],int(font[2])]
    else:
        font=[fontset['name'],fontset['style'],fontset['size']]
    if height:
        height=float(height)
    else: 
        height=20
    if width: 
        width=float(width) 
    else: 
        width=0
    if position:
        position=position.split(',')
        position=[x+float(position[0]),y+float(position[1])]
    if stretch:
        stretch=True
    else:
        stretch=False
    if linebreak:
        linebreak=1
    else:
        linebreak=0
    if nameclass=='Line':
        if not position:
            position=[pageset['x'],pageset['y']]
        MaxY=DrawLine(bandheight,y,position,width,height,stretch)
    elif nameclass=='Field':
        if 'SumFor' in expression:
            sumfield = expression.split(',')[0].replace('SumFor(','')
            condfield = expression.split(',')[1].replace(')','')
            keyvalue = row[condfield]            
            newvalue=SumFor(sumfield,condfield,keyvalue)
        else:
            newvalue=CalcExpression(expression,row)
        if not calcualte:
            text=str(newvalue) if isinstance(newvalue,str) else StrFloat(newvalue)
        else:
            value=Calculate(nameobject,calcualte,newvalue)
            if isinstance(value,str):
                text=value
            else:
                text=StrFloat(value)
        MaxY=DrawText(bandheight,y,text,border,width,height,stretch,font,align,linebreak) 
    elif nameclass=='SumBefore':
        sumfield, condfield = expression.split(",") 
        keyvalue = row[condfield]
        text=str(SumFor(sumfield,condfield,keyvalue))
        MaxY=DrawText(bandheight,y,text,border,width,height,stretch,font,align,linebreak)
    else:
        if width==0:
            width=pageset['width']
        MaxY=DrawText(bandheight,y,text,border,width,height,stretch,font,align,linebreak)
    return MaxY  

def DrawLine(bandheight,y,position,width,height,stretch,pen=0.3):
    x1, y1 = position
    x2 = x1 + width
    y2 = y1 + height
    if x1==x2 and stretch:
        y2 = y + bandheight
        
    pdf.set_line_width(pen)    
    pdf.line(x1,y1,x2,y2)
    return y2

def DrawText(bandheight,y,text,border,width=80,height=45,stretch=False,font=['Times','',10],align='Left',linebreak=0):
    global pdf
    SetFont(font)
    if stretch:
        texts=WrapText(text,width,font)
    else:
        widthtext=pdf.get_string_width(text)
        if width<widthtext:
            countchar=len(text)
            for i in range(countchar-1,0,-1):
                subtext=text[:i]                
                widthtext=pdf.get_string_width(subtext)
                if width<widthtext:
                    texts=[subtext]
        else:
            texts=[text]
    for text in texts:
        if align=='Center':
            pdf.cell(width,height,text,border,linebreak,'C')
        elif align=='Right':
            pdf.cell(width,height,text,border,linebreak,'R')
        else:
            pdf.cell(width,height,text,border,linebreak)
        y+=height
    y-=height
    return y
        
def WrapText(text,width,font):
    global pdf
    words=text.split(" ")
    countwords=len(words)
    texts=[]
    subtext=''
    lasttext=''
    SetFont(font)
    for word in words:
        if subtext=='':
            subtext = word
        else:
            subtext += " " + word
        widthtext=pdf.get_string_width(subtext)
        if widthtext>width:
            texts.append(lasttext)
            subtext = word
            lasttext = ''
        else:
            lasttext = subtext
    if lasttext!='':
        texts.append(lasttext)
    else:
        if subtext!='':
            texts.append(subtext)
    return texts

def SumFor(sumfield,condfield,keyvalue):
    global dicTables, tableset
    rows=dicTables[tableset]
    result=0
    for row in rows:
        if row[condfield]==keyvalue:
            result += row[sumfield]
    return result

def InitCalculate():
    global dicCalculates, lstResults
    lstResults=[]
    lstChilds=GetChilds('simplereport')
    for child in lstChilds:
        init, calculate, resetwhen  = GetAttribute(child,'init','calculate','reset')
        if calculate in ['SUM','COUNT','MAX','MIN']:
            dicCalculate={}
            dicCalculate['initvalue']=int(init)
            dicCalculate['resetwhen']=resetwhen
            dicCalculate['value']=int(init)
            dicCalculates[child]=dicCalculate

def CalcExpression(expression,row=None):
    lstSigns=list('*/+-()=<>[]')
    for sign in lstSigns:
        newsign = ";"+sign+";"
        expression = expression.replace(sign,newsign)
    lstExprs = expression.split(";")
    strEval = ""
    lstSigns.append("' '")
    lstSigns.append('" "')
    for expr in lstExprs:
        if expr in lstSigns:
            strEval += expr
        else:
            try:
                value=row[expr]
            except:
                try:
                    value=GetVariable(expr)
                except:
                    try:
                        value=GetParameter(expr)
                    except:
                        value=None
            if value==None:
                value=expr
            elif isinstance(value,str):
                value="'"+value+"'"
            else:
                value=str(value)
            strEval+=value
    try:
        return eval(strEval)
    except:
        return None

def ComandSqlite(expression,row=None):
    expression = expression.replace("+",";")
    lstExprs = expression.split(";")
    strEval = ""
    for expr in lstExprs:
        try:
            value=row[expr]
        except:
            try:
                value=GetVariable(expr)
            except:
                try:
                    value=GetParameter(expr)
                except:
                    value=None
        if value==None:
            value=expr
        elif isinstance(value,str):
            value=str(value)
        strEval+=value
    return strEval

def ResetWhen(namegroup):
    global dicCalculates, dicVariables
    for variable in dicVariables:
        dicVariable=dicVariables[variable]
        if dicVariable['resetwhen']==namegroup:
            dicVariable['value']=dicVariable['initvalue']
            dicVariables[variable]=dicVariable
    for calculate in dicCalculates:
        dicCalculate=dicCalculates[calculate]
        if dicCalculate['resetwhen']==namegroup:
            dicCalculate['value']=dicCalculate['initvalue']
            dicCalculates[calculate]=dicCalculate

def NewPage():
    global pageset, pdf
    pageset['pageno']=pdf.page_no()
    pageset['y']=pageset['topmargin']
    pdf.set_top_margin(pageset['topmargin'])
    if pageset['pageno']%2==0:
        pdf.set_left_margin(pageset['leftmargin'])
        pdf.set_right_margin(pageset['rightmargin']+pageset['gutter'])
        pageset['x']=pageset['leftmargin']
    else:
        pdf.set_left_margin(pageset['leftmargin']+pageset['gutter'])
        pdf.set_right_margin(pageset['rightmargin'])
        pageset['x']=pageset['gutter']+pageset['leftmargin']
    pageset['height']=pdf.h-pageset['topmargin']-pageset['bottommargin']
    pageset['width']=pdf.w-pageset['gutter']-pageset['leftmargin']-pageset['rightmargin']
    if pageset['pageno']==1:
        DrawBand('title') 
    else:
        ResetWhen('page')
    DrawBand('header')

def CheckNewGroup(row):
    global dicGroups

def StartGroup():
    global lstParents, dicAttrs, lstResults, dicGroups
    lstResults=[]
    lstChilds=GetChilds('content')
    for child in lstChilds:
        nameclass, expression, height, reprintnewpage, startnewpage = GetAttribute(child,'class','expression','height','reprintnewpage','startnewpage')
        if nameclass=='Group':
            dicGroup={}
            if reprintnewpage:
                dicGroup['reprintnewpage'] =  True 
            else:
                dicGroup['reprintnewpage'] =  False
            if startnewpage:
                dicGroup['startnewpage'] =  True 
            else:
                dicGroup['startnewpage'] =  False           
            dicGroup['expression']=expression
            dicGroup['height']=height
            dicGroup['value']=''
            dicGroup['count']=0
            dicGroups[child]=dicGroup

def OnGroupHeader(row):
    global dicGroups
    for group in dicGroups:
        dicGroup=dicGroups[group]
        key = dicGroup['expression']
        if row[key]!=dicGroup['value']:
            if dicGroup['count']>1:
                namefooter=group.replace('header','footer')
                DrawBand(namefooter,row)
            dicGroup['count']=1
            dicGroup['value']=row[key]
            dicGroups[group]=dicGroup
            ResetWhen(group)
            DrawBand(group,row)
        else:
            dicGroup['count']+=1
            dicGroups[group]=dicGroup

def OnGroupFooter(row):
    global dicGroups
    for group in dicGroups:
        namefooter=group.replace('header','footer')
        DrawBand(namefooter,row)

def PageSetup():
    name, margin, landscape, bothside = GetAttribute('pagesetup','name','margin','landscape','bothside')
    pageset['pagesize']=name
    if landscape:
        pageset['oriental']="L"
    else:
        pageset['oriental']="P"
    if bothside:
        pageset['bothside']=True
    else:
        pageset['bothside']=False
    margin=margin.split(',')
    pageset['topmargin']=float(margin[0])
    pageset['leftmargin']=float(margin[1])
    pageset['rightmargin']=float(margin[2])
    pageset['bottommargin']=float(margin[3])
    pageset['gutter']=float(margin[4])
    pageset['unit']='pt'

def FontSetup():
    global pdf
    name,style,size=GetAttribute('defaultfont','font','style','size')
    fontset['name']=name
    fontset['style']=style
    fontset['size']=int(size)
    font=[fontset['name'],fontset['style'],fontset['size']]
    SetFont(font)

def AddFonts():
    global lstResults
    lstResults=[]
    lstChilds=GetChilds('addfont')
    for child in lstChilds:
        family,_ = GetAttribute(child,'family',None)
        namefont, style, ttffile, uni = family.split(",")
        if uni:
            uni=True
        else:
            uni=False
        pdf.add_font(namefont,style,ttffile,uni)

def SetFont(fontset):
    namefont, style, size = fontset
    global pdf
    pdf.set_font(namefont,style,size)
    
def BuildReport(xmlFile,pdfFile,**kwargs):
    global parser, pdf, dicParameters, lstParents, dicAttrs, tableset, lstResults
    with open(xmlFile,mode='r',encoding='utf-8') as file:
        docs=file.read()
        file.close()
    parser.feed(docs)
    lstParents=parser.lstParents
    dicAttrs=parser.dicAttrs
    
    #page setup
    PageSetup()
    pdf=FPDF(pageset['oriental'],pageset['unit'],pageset['pagesize'])
    pdf.add_page()

    #font default
    AddFonts()
    FontSetup()
    #parameters
    strParameters,_=GetAttribute('parameters','list',None)
    lstParameters=strParameters.split(',')
    for pvar, pvalue in kwargs.items():
        if pvar in lstParameters:
            dicParameters[pvar]=pvalue
    #data

    #tables    
    lstResults=[]    
    lstTables=GetChilds('table')
    for table in lstTables:
        nameclass,band=GetAttribute(table,'class','band')
        if nameclass=='sqlite3':
            command,_=GetAttribute(table,'command',None)
            command=ComandSqlite(command,None)
            command=command.replace("[","'").replace("]","'")
            rows=eval(command)
            dicTables[table]=rows
        if band=='detail':
            tableset=table
    if tableset=='':
        tableset=None
        
    #variables
    InitVariable()

    #content
    InitCalculate()
    NewPage()
    StartGroup()
    rows=dicTables[tableset]
    for row in rows:
        #variable
        CalcVariable(row)
        #calculate
        OnGroupHeader(row)
        DrawBand('detail',row)
        CalcCaculate(row)
        print(dicCalculates)
    
    OnGroupFooter(row)   
    DrawBand('footer')
    
    #summary 
    DrawBand('summary')    
     
    pdf.output(pdfFile)
    
if __name__=='__main__':
    BuildReport("C:/Dung/fpdfsample.xml","C:/Dung/Sample.pdf",UserCode='000',UserName='Nguyen Ton Le',FrDate='2022-01-01',ToDate='2022-12-01')
