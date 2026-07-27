public static List<ScoringNotesViewModel> ScoringNotesByProject(int Numero_DemandeFinan)// calcul de scoring par projet
        {
            BfpmeDBEntities DB = new BfpmeDBEntities();
            List<int> ListeNotationAnnulle = DB.ScoringNotationAnnulation.Select(c => c.CodeNotation).ToList();
            if (!DB.ScoringNotation.Any(c => c.CodeDemandeFinancement == Numero_DemandeFinan && !ListeNotationAnnulle.Contains(c.Code))) return new List<ScoringNotesViewModel>();
            ScoringNotation ScoringNotation = DB.ScoringNotation.Where(c => c.CodeDemandeFinancement == Numero_DemandeFinan && !ListeNotationAnnulle.Contains(c.Code)).OrderByDescending(c => c.DateNotation).FirstOrDefault();
            int CodeModeleNotaion = ScoringNotation.CodeModeleNotation;
            List<ScoringPonderationSousFacteurViewModel> ListeDonneesDuSommaire = CalculWeightsDesSousFacteurs().Where(c => c.CodeModeleNotation == CodeModeleNotaion).ToList(); ;
            decimal SommeScoreByWeightGoodFinancialMin = ListeDonneesDuSommaire.Sum(c => (decimal)c.ScoreByWeightGoodFinancialMinWithoutKillingFactor);
            decimal SommeScoreByWeightAverageFinancialMin = ListeDonneesDuSommaire.Sum(c => (decimal)c.ScoreByWeightAverageFinancialMinWthoutKillingFactors);
            decimal SommeScoreByWeightGoodFinancialMax = ListeDonneesDuSommaire.Sum(c => (decimal)c.ScoreByWeightGoodFinancialMax);
            decimal SommeScoreByWeightAverageFinancialMax = ListeDonneesDuSommaire.Sum(c => (decimal)c.ScoreByWeightAverageFinancialMax);
            decimal MinSommeScoreByWeightGoodAndAverafeFinancial = SommeScoreByWeightGoodFinancialMin < SommeScoreByWeightAverageFinancialMin ? SommeScoreByWeightGoodFinancialMin : SommeScoreByWeightAverageFinancialMin;
            decimal MaxSommeScoreByWeightGoodAndAverafeFinancial = SommeScoreByWeightGoodFinancialMax > SommeScoreByWeightAverageFinancialMax ? SommeScoreByWeightGoodFinancialMax : SommeScoreByWeightAverageFinancialMax;

            List<int> ListeCodeCritereNonDisponible = DB.ScoringRUCritere.Where(c => c.NonDisponible == true).Select(c => c.Code).ToList();
            List<int> ListeCodeSousFactereNonNonDisponible = DB.ScoringRUSousFacteurParModele.Where(c => c.AccepteNonDisponible == false).Select(c => c.CodeSousFacteur).ToList();
            List<int> ListeCodeCritereDuSousFactereNonNonDisponible = DB.ScoringRUCritereNotes.Where(c => ListeCodeSousFactereNonNonDisponible.Contains(c.CodeSousFacteur) && ListeCodeCritereNonDisponible.Contains(c.CodeCritere)).Select(c => c.CodeCritere).Distinct().ToList();
            List<int> ListeCodeCritereEliminatoire = DB.ScoringRUCritereNotes.Where(c => c.Eliminatoire == true).Select(c => c.CodeCritere).ToList();
            List<int> ListeCodeSousFacteurValeurObligatoire = DB.ScoringRUSousFacteurParModele.Where(c => c.ValeurCritereObligatoire == true && c.CodeModeleNotation == CodeModeleNotaion).Select(c => c.CodeSousFacteur).ToList();
            List<ScoringPonderationSousFacteurViewModel> ListePonderationSousFacteur = ListeDonneesDuSommaire;
            List<int> ListeSousFacteurparModele = DB.ScoringRUSousFacteurParModele.Where(c => c.CodeModeleNotation == CodeModeleNotaion).Select(c => c.CodeSousFacteur).ToList();
            List<ScoringNotesViewModel> result =
                (from ScoringNotes in DB.ScoringNotes.Where(c => c.CodeNotation == ScoringNotation.Code && ListeSousFacteurparModele.Contains(c.CodeSousFacteur)).ToList()
                 select new ScoringNotesViewModel
                 {
                     Code = ScoringNotes.Code,
                     CodeNotation = ScoringNotes.CodeNotation,
                     CodeModeleNotation = ScoringNotes.ScoringNotation.CodeModeleNotation,
                     CodeTypeIdentifiant = ScoringNotes.ScoringNotation.CodeTypeIdentifiant,
                     NumeroIdentifiant = ScoringNotes.ScoringNotation.NumeroIdentifiant,
                     CodeDemandeFinancement = ScoringNotes.ScoringNotation.CodeDemandeFinancement,
                     CodeClient = ScoringNotes.ScoringNotation.CodeClient,
                     CodeSousFacteur = ScoringNotes.CodeSousFacteur,
                     CodeCritere = ScoringNotes.CodeCritere!=null? (int)ScoringNotes.CodeCritere:0,
                     Valeur = ScoringNotes.Valeur,
                     DateNotation = ScoringNotes.DateNotation,
                     CodeFacteur = DB.ScoringRUSousFacteurParModele.Where(c => c.CodeSousFacteur == ScoringNotes.CodeSousFacteur && c.CodeModeleNotation == ScoringNotes.ScoringNotation.CodeModeleNotation).FirstOrDefault().CodeFacteur,
                     SousFacteur = DB.ScoringRUSousFacteurParModele.Where(c => c.CodeSousFacteur == ScoringNotes.CodeSousFacteur && c.CodeModeleNotation == ScoringNotes.ScoringNotation.CodeModeleNotation).FirstOrDefault().CodeFacteur != null ? DB.ScoringRUSousFacteur.Where(p => p.Code == ScoringNotes.CodeSousFacteur).FirstOrDefault().Libelle : "",
                                     
                      NonDisponible =ScoringNotes.CodeCritere>0 ? ListeCodeCritereDuSousFactereNonNonDisponible.Contains((int)ScoringNotes.CodeCritere) ? true : false :false,
                     CritereEliminatoire = ScoringNotes.CodeCritere>0 ?ListeCodeCritereEliminatoire.Contains((int)ScoringNotes.CodeCritere):false,
                     ValeurCritereObligatoire = ScoringNotes.CodeSousFacteur>0?ListeCodeSousFacteurValeurObligatoire.Contains(ScoringNotes.CodeSousFacteur):false,
                 }).ToList();
            decimal NbElement=result.Count();
            List<ScoringSummaryViewModel> ListeEtatSummary = ScoringService.ListeEtatSummary((int)CodeModeleNotaion);// le Modèle de notation
          
            bool ExisteNonDiusponiple = result.Any(c =>ListeCodeSousFactereNonNonDisponible.Contains((int)c.CodeSousFacteur)&& ListeCodeCritereDuSousFactereNonNonDisponible.Contains(c.CodeCritere));
            decimal NoteSeuildeCalul = -70;
            foreach( ScoringNotesViewModel Item in result)
            {
                int NombreCritereSousFacteurSupSeuil = (DB.ScoringRUCritereNotes.Where(c => (c.CodeSousFacteur == Item.CodeSousFacteur) && (c.CodeModeleNotation == Item.CodeModeleNotation) && (c.Note >= NoteSeuildeCalul)).Count());
                int NbreCritereSousFacteurSup0 =( DB.ScoringRUCritereNotes.Where(c => (c.CodeSousFacteur == Item.CodeSousFacteur) && (c.CodeModeleNotation == Item.CodeModeleNotation)&&(c.Note>=0)).Count());
                decimal MoyenneNoteSousFacteur = DB.ScoringRUCritereNotes.Where(c => (c.CodeSousFacteur == Item.CodeSousFacteur) && (c.CodeModeleNotation == Item.CodeModeleNotation)).Sum(c => c.Note > 0 ? (decimal)c.Note : 0) / NbreCritereSousFacteurSup0;
                Item.Facteur =Item.CodeFacteur+" : "+ DB.ScoringRUFacteur.Where(c => c.Code == Item.CodeFacteur).FirstOrDefault().Libelle;
                     Item.PonderationFacteur =DB.ScoringRUFacteursParModele.Where(c=>c.CodeFacteur==(Item.CodeFacteur)&& (c.CodeModeleNotation==Item.CodeModeleNotation)).FirstOrDefault().Ponderation;
                     Item.NotePondereSousFacteurGoodFinancial =ListePonderationSousFacteur.Where(c=>c.CodeModeleNotation==Item.CodeModeleNotation && c.CodeFacteur==Item.CodeFacteur &&c.CodeSousFacteur==Item.CodeSousFacteur).FirstOrDefault().GoodPonderationSousFacteur;
                     Item.NotePondereSousFacteurAverageFinancial = ListePonderationSousFacteur.Where(c => c.CodeModeleNotation == Item.CodeModeleNotation && c.CodeFacteur == Item.CodeFacteur && c.CodeSousFacteur == Item.CodeSousFacteur).FirstOrDefault().AveragePonderationSousFacteur;
                     Item.FacteurPonderation = Item.Facteur + " (" + Item.PonderationFacteur + ")";
                     Item.SousFacteurPonderation = Item.SousFacteur + " ( Good.F" + Item.NotePondereSousFacteurGoodFinancial + "  Average.F"+ Item.NotePondereSousFacteurAverageFinancial+")";
               
                     Item.NoteAttribuee = Item.CodeCritere > 0 ? (!ListeCodeCritereNonDisponible.Contains((int)Item.CodeCritere) ? (DB.ScoringRUCritereNotes.Any(c => c.CodeCritere == Item.CodeCritere && c.CodeSousFacteur == Item.CodeSousFacteur && c.CodeModeleNotation == Item.CodeModeleNotation) ? (DB.ScoringRUCritereNotes.Where(c => c.CodeCritere == Item.CodeCritere && c.CodeSousFacteur == Item.CodeSousFacteur && c.CodeModeleNotation == Item.CodeModeleNotation).FirstOrDefault().Note.HasValue ? DB.ScoringRUCritereNotes.Where(c => c.CodeCritere == Item.CodeCritere && c.CodeSousFacteur == Item.CodeSousFacteur && c.CodeModeleNotation == Item.CodeModeleNotation).FirstOrDefault().Note : 0) : 0) : (((DB.ScoringRUCritereNotes.Where(c => c.CodeSousFacteur == Item.CodeSousFacteur && c.CodeModeleNotation == Item.CodeModeleNotation).Sum(c => c.Note > NoteSeuildeCalul ? c.Note : 0)) / NombreCritereSousFacteurSupSeuil))) : 0;
                     Item.NotePondereCritereGoodFinancial = Item.NoteAttribuee * Item.NotePondereSousFacteurGoodFinancial / 100;
                     Item.NotePondereCritereAverageFinancial = Item.NoteAttribuee * Item.NotePondereSousFacteurAverageFinancial / 100;
                    
                     Item.ScoreCalculeGoodFinancial = ExisteNonDiusponiple ? 0 : (((decimal)Item.NotePondereCritereGoodFinancial - MinSommeScoreByWeightGoodAndAverafeFinancial / NbElement) * 200 / (MaxSommeScoreByWeightGoodAndAverafeFinancial - MinSommeScoreByWeightGoodAndAverafeFinancial)) + 100 / NbElement;
                     Item.ScoreCalculeAverageFinancial = ExisteNonDiusponiple ? 0 : (((decimal)Item.NotePondereCritereAverageFinancial - MinSommeScoreByWeightGoodAndAverafeFinancial / NbElement) * 200 / (MaxSommeScoreByWeightGoodAndAverafeFinancial - MinSommeScoreByWeightGoodAndAverafeFinancial)) + 100 / NbElement;
                Item.Critere = Item.CodeCritere > 0 ?DB.ScoringRUCritere.Where(c=>c.Code==Item.CodeCritere).FirstOrDefault().Libelle:"";
               
            }

                   
            return result;
        }


// Modèle de notation avec tous ces détails
 public static List<ScoringSummaryViewModel> ListeEtatSummary(int CodeModeleScoring)
        {
            BfpmeDBEntities DB = new BfpmeDBEntities();

            var nfi = (System.Globalization.NumberFormatInfo)System.Globalization.CultureInfo.InvariantCulture.NumberFormat.Clone();
            nfi.NumberGroupSeparator = " ";

            List<ScoringSummaryViewModel> Resultat = new List<ScoringSummaryViewModel>();
            List<ScoringRUCritereNotes> ListeCritereNoteParModele = DB.ScoringRUCritereNotes.Where(c => c.CodeModeleNotation == CodeModeleScoring).ToList();

              List<ScoringRUFacteursParModeleViewModel> ListeFacteur = ScoringRUFacteursParModeleAll().Where(c => c.CodeModeleNotation == CodeModeleScoring).ToList();
            
            foreach (ScoringRUFacteursParModeleViewModel Facteur in ListeFacteur)
            {
                int MaxPrioriteSousfacteur = (int)DB.ScoringRUSousFacteurParModele.Where(c => c.CodeModeleNotation == CodeModeleScoring && c.CodeFacteur == Facteur.CodeFacteur).Max(c => c.Priorite);
                int NbreSousFacteurparFacteur = (int)DB.ScoringRUSousFacteurParModele.Where(c => c.CodeModeleNotation == CodeModeleScoring && c.CodeFacteur == Facteur.CodeFacteur).Count();

                // (decimal) (MaxPrioriteSousfacteur + 1 - SousFacteur.Priorite) / NbreSousFacteurparFacteur
                List<ScoringRUSousFacteurParModeleViewModel> ListeSousFacteurParFacteur = ScoringRUSousFacteurParModeleAll().Where(c => (c.CodeModeleNotation == CodeModeleScoring) && (c.CodeFacteur == Facteur.CodeFacteur)).ToList();
                decimal SommeMoyennePrioriteSousfacteur = MaxPrioriteSousfacteur + 1 - ListeSousFacteurParFacteur.Sum(c => c.Priorite != null ? (decimal)(c.Priorite) : 0) / NbreSousFacteurparFacteur;
                //Sub Weights
                decimal SubWeights = 0;
                decimal Weights = 0;

                //Weights
                decimal WeightGoodFinancial = 0;
                decimal WeightAverageFinancial = 0;

                // Scores (Not Weighted)
                decimal Min = 0;
                decimal ScoreNotWeightedMinWithoutKillingFactor = 0;
                decimal ScoreNotWeightedMax = 0;
                decimal ScoreNotWeitedRangeWithoutKillingFactor = 0;
                // Weighted Scores (By Weight) GoodFinancial
                decimal ScoreNotWeightedRange = 0;
                decimal ScoreByWeightGoodFinancialMin = 0;
                decimal ScoreByWeightGoodFinancialMinWithoutKillingFactor = 0;
                decimal ScoreByWeightGoodFinancialMax = 0;
                decimal ScoreByWeightGoodFinancialRange = 0;
                decimal ScoreByWeightGoodFinancialRangeWithoutKillingFactor = 0;
                // Weighted Scores (By Weight) AverageFinancial
                decimal ScoreByWeightAverageFinancialMin = 0;
                decimal ScoreByWeightAverageFinancialMinWthoutKillingFactors = 0;
                decimal ScoreByWeightAverageFinancialMax = 0;
                decimal ScoreByWeightAverageFinancialRange = 0;
                decimal ScoreByWeightAverageFinancialRangelWthoutKillingFactors = 0;
                //Overall

                decimal MinOverall = 0;
                decimal MaxOverall = 0;

                //Sub Weights par Facteur
                decimal FacteurSubWeights = 0;
                decimal FacteurWeights = 0;

                //Weights par facteur
                decimal FacteurWeightGoodFinancial = 0;
                decimal FacteurWeightAverageFinancial = 0;

                // Scores (Not Weighted) par facteur
                decimal FacteurMinNotWeighted = 0;
                decimal FacteurMinWthoutKillingFactors = 0;
                decimal FacteurMaxNotWeighted = 0;
                decimal FacteurRangeWthoutKillingFactors = 0;
                // Weighted Scores (By Weight) GoodFinancial par facteur
                decimal FacteurMinByWeightGoodFinancial = 0;
                decimal FacteurMinByWeightGoodFinancialWthoutKillingFactors = 0;
                decimal FacteurMaxByWeightGoodFinancial = 0;
                decimal FacteurRangeByWeightGoodFinancial = 0;
                decimal FacteurRangeByWeightGoodFinancialWthoutKillingFactors = 0;
                // Weighted Scores (By Weight) AverageFinancial par facteur
                decimal FacteurMinByWeightAverageFinancial = 0;
                decimal FacteurMinByWeightAverageFinancialWthoutKillingFactors = 0;
                decimal FacteurMaxByWeightAverageFinancial = 0;
                decimal FacteurRangeByWeightAverageFinancial = 0;
                decimal FacteurRangeByWeightAverageFinancialWthoutKillingFactors = 0;
                //Overall par facteur

                decimal FacteurMinOverall = 0;
                decimal FacteurMaxOverall = 0;




                foreach (ScoringRUSousFacteurParModeleViewModel SousFacteur in ListeSousFacteurParFacteur)
                {
                    decimal PrioriteMoyenneSousFacteur = SousFacteur.Priorite != null ? ((decimal)(MaxPrioriteSousfacteur + 1 - SousFacteur.Priorite) / NbreSousFacteurparFacteur) : ((decimal)(MaxPrioriteSousfacteur + 1) / NbreSousFacteurparFacteur);

                    List<ScoringRUCritereNotes> ListeCritereNoteParSousFacteur = ListeCritereNoteParModele.Where(c => c.CodeSousFacteur == SousFacteur.CodeSousFacteur).ToList();
                    SubWeights = PrioriteMoyenneSousFacteur * 100 / (SommeMoyennePrioriteSousfacteur);
                    Weights = SubWeights / 100 * (decimal)SousFacteur.Ponderation;
                    //Weights
                    WeightGoodFinancial = SubWeights / 100 * (decimal)SousFacteur.PonderationGoodFinancial;
                    WeightAverageFinancial = SubWeights / 100 * (decimal)SousFacteur.PonderationAverageFinancial;
                    // Scores (Not Weighted)
                    Min = (decimal)ListeCritereNoteParSousFacteur.Where(c => c.Note != null).Min(c => c.Note);

                    ScoreNotWeightedMinWithoutKillingFactor = (decimal)SousFacteur.MinWithoutKillingFactors;
                    ScoreNotWeightedMax = (decimal)ListeCritereNoteParSousFacteur.Where(c => c.Note != null).Max(c => c.Note);
                    ScoreNotWeitedRangeWithoutKillingFactor = ScoreNotWeightedMax - ScoreNotWeightedMinWithoutKillingFactor;
                    ScoreNotWeightedRange = ScoreNotWeightedMax - Min;
                    // Weighted Scores (By Weight) GoodFinancial
                    ScoreByWeightGoodFinancialMin = Min * WeightGoodFinancial / 100;
                    ScoreByWeightGoodFinancialMinWithoutKillingFactor = ScoreNotWeightedMinWithoutKillingFactor * WeightGoodFinancial / 100;
                    ScoreByWeightGoodFinancialMax = ScoreNotWeightedMax * WeightGoodFinancial / 100;
                    ScoreByWeightGoodFinancialRange = ScoreNotWeightedRange * WeightGoodFinancial / 100;
                    ScoreByWeightGoodFinancialRangeWithoutKillingFactor = ScoreNotWeitedRangeWithoutKillingFactor * WeightGoodFinancial / 100;
                    // Weighted Scores (By Weight) AverageFinancial
                    ScoreByWeightAverageFinancialMin = Min * WeightAverageFinancial / 100;
                    ScoreByWeightAverageFinancialMinWthoutKillingFactors = ScoreNotWeightedMinWithoutKillingFactor * WeightAverageFinancial / 100;
                    ScoreByWeightAverageFinancialMax = ScoreNotWeitedRangeWithoutKillingFactor * WeightAverageFinancial / 100;
                    ScoreByWeightAverageFinancialRange = ScoreNotWeitedRangeWithoutKillingFactor * WeightAverageFinancial / 100;
                    ScoreByWeightAverageFinancialRangelWthoutKillingFactors = ScoreNotWeitedRangeWithoutKillingFactor * WeightAverageFinancial / 100;
                    //Overall
                    MinOverall = ScoreByWeightAverageFinancialMinWthoutKillingFactors > ScoreByWeightGoodFinancialMinWithoutKillingFactor ? ScoreByWeightGoodFinancialMinWithoutKillingFactor : ScoreByWeightAverageFinancialMinWthoutKillingFactors;
                    MaxOverall = ScoreByWeightAverageFinancialMax > ScoreByWeightGoodFinancialMax ? ScoreByWeightGoodFinancialMax : ScoreByWeightAverageFinancialMax;



                      //Sub Weights par Facteur
                    FacteurSubWeights += SubWeights;
                    FacteurWeights += Weights;

                    //Weights par facteur
                    FacteurWeightGoodFinancial += WeightGoodFinancial;
                    FacteurWeightAverageFinancial += WeightAverageFinancial;

                    // Scores (Not Weighted) par facteur
                    FacteurMinNotWeighted += Min;
                    FacteurMinWthoutKillingFactors += ScoreNotWeightedMinWithoutKillingFactor;
                    FacteurMaxNotWeighted += ScoreNotWeightedMax;
                    FacteurRangeWthoutKillingFactors += ScoreNotWeitedRangeWithoutKillingFactor;
                    // Weighted Scores (By Weight) GoodFinancial par facteur
                    FacteurMinByWeightGoodFinancial += ScoreByWeightGoodFinancialMin;
                    FacteurMinByWeightGoodFinancialWthoutKillingFactors += ScoreByWeightGoodFinancialMinWithoutKillingFactor;
                    FacteurMaxByWeightGoodFinancial += ScoreByWeightGoodFinancialMax;
                    FacteurRangeByWeightGoodFinancial += ScoreByWeightGoodFinancialRange;
                    FacteurRangeByWeightGoodFinancialWthoutKillingFactors += ScoreByWeightGoodFinancialRangeWithoutKillingFactor;
                    // Weighted Scores (By Weight) AverageFinancial par facteur
                    FacteurMinByWeightAverageFinancial += ScoreByWeightAverageFinancialMin;
                    FacteurMinByWeightAverageFinancialWthoutKillingFactors += ScoreByWeightAverageFinancialMinWthoutKillingFactors;
                    FacteurMaxByWeightAverageFinancial += ScoreByWeightAverageFinancialMax;
                    FacteurRangeByWeightAverageFinancial += ScoreByWeightAverageFinancialRange;
                    FacteurRangeByWeightAverageFinancialWthoutKillingFactors += ScoreByWeightAverageFinancialRangelWthoutKillingFactors;
                    //Overall par facteur

                    FacteurMinOverall += MinOverall;
                    FacteurMaxOverall += MaxOverall;
                    ScoringSummaryViewModel summary = new ScoringSummaryViewModel();
                    summary.FacteurMaxByWeightAverageFinancial = FacteurMaxByWeightAverageFinancial;
                    summary.FacteurMaxByWeightGoodFinancial = FacteurMaxByWeightGoodFinancial;
                    summary.FacteurMaxNotWeighted = FacteurMaxNotWeighted;
                    summary.FacteurMaxOverall = FacteurMaxOverall;
                    summary.FacteurMinByWeightAverageFinancial = FacteurMinByWeightAverageFinancial;
                    summary.FacteurMinByWeightAverageFinancialWthoutKillingFactors = FacteurMinByWeightAverageFinancialWthoutKillingFactors;
                    summary.FacteurMinByWeightGoodFinancial = FacteurMinByWeightGoodFinancial;
                    summary.FacteurMinByWeightGoodFinancialWthoutKillingFactors = FacteurMinByWeightGoodFinancialWthoutKillingFactors;
                    summary.FacteurMinNotWeighted = FacteurMinNotWeighted;
                    summary.FacteurMinOverall = FacteurMinOverall;
                    summary.FacteurMinWthoutKillingFactors = FacteurMinWthoutKillingFactors;
                    summary.FacteurRangeByWeightAverageFinancial = FacteurRangeByWeightAverageFinancial;
                    summary.FacteurRangeByWeightAverageFinancialWthoutKillingFactors = FacteurRangeByWeightAverageFinancialWthoutKillingFactors;
                    summary.FacteurRangeByWeightGoodFinancial = FacteurRangeByWeightGoodFinancial;
                    summary.FacteurRangeByWeightGoodFinancialWthoutKillingFactors = FacteurRangeByWeightGoodFinancialWthoutKillingFactors;
                    summary.FacteurRangeWthoutKillingFactors = FacteurRangeWthoutKillingFactors;
                    summary.FacteurSubWeights = FacteurSubWeights;
                    summary.FacteurWeightAverageFinancial = FacteurWeightAverageFinancial;
                    summary.FacteurWeightGoodFinancial = FacteurWeightGoodFinancial;
                    summary.FacteurWeights = FacteurWeights;
                    summary.MaxOverall = MaxOverall;
                    summary.Min = Min;
                    summary.MinOverall = MinOverall;
                    summary.ScoreByWeightAverageFinancialMax = ScoreByWeightAverageFinancialMax;
                    summary.ScoreByWeightAverageFinancialMin = ScoreByWeightAverageFinancialMin;
                    summary.ScoreByWeightAverageFinancialMinWthoutKillingFactors = ScoreByWeightAverageFinancialMinWthoutKillingFactors;
                    summary.ScoreByWeightAverageFinancialRange = ScoreByWeightAverageFinancialRange;
                    summary.ScoreByWeightAverageFinancialRangelWthoutKillingFactors = ScoreByWeightAverageFinancialRangelWthoutKillingFactors;
                    summary.ScoreByWeightGoodFinancialMax = ScoreByWeightGoodFinancialMax;
                    summary.ScoreByWeightGoodFinancialMin = ScoreByWeightGoodFinancialMin;
                    summary.ScoreByWeightGoodFinancialMinWithoutKillingFactor = ScoreByWeightGoodFinancialMinWithoutKillingFactor;
                    summary.ScoreByWeightGoodFinancialRange = ScoreByWeightGoodFinancialRange;
                    summary.ScoreByWeightGoodFinancialRangeWithoutKillingFactor = ScoreByWeightGoodFinancialRangeWithoutKillingFactor;
                    summary.ScoreNotWeightedMax = ScoreNotWeightedMax;
                    summary.ScoreNotWeightedMinWithoutKillingFactor = ScoreNotWeightedMinWithoutKillingFactor;
                    summary.ScoreNotWeightedRange = ScoreNotWeightedRange;
                    summary.ScoreNotWeitedRangeWithoutKillingFactor = ScoreNotWeitedRangeWithoutKillingFactor;
                    summary.SubWeights = SubWeights;
                    summary.WeightAverageFinancial = WeightAverageFinancial;
                    summary.WeightGoodFinancial = WeightGoodFinancial;
                    summary.Weights = Weights;
                    summary.CodeFacteur = SousFacteur.CodeFacteur;
                    summary.CodeSousFacteur = SousFacteur.CodeSousFacteur;
                    Resultat.Add(summary);
                }
                

            }
           

            return Resultat;
        }