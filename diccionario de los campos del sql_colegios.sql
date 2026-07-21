select *
from DwhStage..DocumentadosColegiosMINEDU
where --PeriodoBanner_Sales = '202610'
--and 
CodBanner = 'C06117'

---PeriodoBanner_Sales: periodo de admisiones en la universidad de la persona
--AñoGraduacionAMIED: periodo fin del ministerio de educación
--ZonaInecAMIED: urbano o rural	
--RegimenAMIED: sierra o costa
--ProvinciaAMIED: de donde viene el colegio
-- CantonAMIED: ubicacion del colegio	
--Sostenimiento: fiscal, privado, municipal, fiscomisional	
--CodColegioBanner_Sales: el codigo amie registrado de forma institucional	
--CodColegioAMIED: codigo amie institucional, si no encuentras información en CodColegioBanner_Sales, toma este para el cruce	
--CodBanner: identificacion del colegio de forma institucional	
--NombreInstitucionAMIED: nombre del colegio tomado del ministerio de educación	
--Nuevo_cluster: clusttering que colocamos instutcionalmete TOP, AAA,AA,A,B,Otros	
--BACHILLERATO PENSIÓN: pension del colegio tomado del ministerio de educación, solo para los privados y fiscomisionales, fecha de actualizacion mayo 2026, para municipales y fiscales colocar NA	
--RangoPension: rango de pensiones cad 250 es un nuevo rango	
--EstudiantesFemeninoTercerAñoBACH: total de graduados de colegios femeninos	
--EstudiantesMasculinoTercerAñoBACH: total graduados de colegio masculinos	
--GraduadosColegioAMIED: suma de graduados totales femeninos y masculinos	
--TotalDocumentadosPeriodo: total de documentados en la universidad contemplados "admitidos retirados"	
-- IdBanner: identificacion institcional de cada estudiante	
--Edad: edad del estudiante	
--AdEtapaOport:Origen del candidato, de donde viene	
--CodCarreraBanner_Sales: codigo de carrera en el que se documento la persona	
--Colegiatura: costo de la carrera	
-- ColegiaturaMenosBeca_ valor a pagar del estudiante	
--AdIndRetiro: indicador si esta retirado (retirado, posible retiro y pago completo)	
--AdEstado: (retirado, posible retiro y pago completo)	
--FechaInicioAcademico: fecha del inicio del periodo en udla	
--AdCodColegio: no tomar en cuenta	
--FechaGradoColegio: fecha de graduacion del estudiante	
--DiferenciaMeses: diferencia de meses de fechainicioperiodo-fechagradocolegio	calculo de los meses
--Diferencia: indicador de tiempo	
--L: leads cantidad de postulantes, tomando en cuenta el periodo- amie-cod banner, esto esta en totales no se deben sumar, si no tomar ya el valor final, no hacer cambios o calculos	
--A: afluentes(persona con un interers fijo)cuenta el periodo- amie-cod banner, esto esta en totales no se deben sumar, si no tomar ya el valor final, no hacer cambios o calculos	
--D: documentados (personas que ya pagaron y entregaron documentos)cuenta el periodo- amie-cod banner, esto esta en totales no se deben sumar, si no tomar ya el valor final, no hacer cambios o calculos
