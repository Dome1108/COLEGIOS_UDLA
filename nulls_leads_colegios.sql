Select Periodo,NombreColegio,BannerColegio--,zz.CodAMIE

,SUM(Base) L,SUM(A) A,SUM(D) D 

--into #afluente

from STAGE_OTROS..STG_SalesForce_CadenaComercial CC

--left join (Select distinct CodBanner,CodAMIE from DwhOperacional.dbo.CatInstitucionEducativa) zz on zz.CodBanner = cc.BannerColegio collate database_default

where [Linea de negocio] = 'UG'


GROUP BY Periodo,NombreColegio,BannerColegio--,zz.CodAMIE

ORDER BY 4 DESC,5 DESC,6 DESC
--lead unico 

-- 592414 -- intereses
-- 310099 nulls - 52% intereses

 